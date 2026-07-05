"use client";

import { useEffect, useState } from "react";
import { routes } from "@/lib/constants/routes";
import { getAuthHeader } from "@/lib/api/client";

// ─── Parse Jadwal Fleksibel (Tidak di-hardcode) ──────────────

function parseFlexibleSchedule(instruction: string): string[] {
  const instr = instruction.toLowerCase();

  const hasPagi = instr.includes("pagi");
  const hasSiang = instr.includes("siang");
  const hasSore = instr.includes("sore");
  const hasMalam = instr.includes("malam");

  if (hasPagi || hasSiang || hasSore || hasMalam) {
    const times: string[] = [];
    if (hasPagi) times.push("07:00");
    if (hasSiang) times.push("12:00");
    if (hasSore) times.push("17:00");
    if (hasMalam) times.push("20:00");
    return times;
  }

  const freqMatch = instr.match(/(\d+)\s*x/);
  const freq = freqMatch ? parseInt(freqMatch[1], 10) : 1;

  if (freq === 1) return ["08:00"];
  if (freq === 2) return ["08:00", "20:00"];
  if (freq === 3) return ["07:00", "14:00", "21:00"];
  if (freq === 4) return ["06:00", "12:00", "18:00", "24:00"];

  const times: string[] = [];
  const startHour = 6;
  const endHour = 22;
  const interval = (endHour - startHour) / (freq - 1 || 1);
  
  for (let i = 0; i < freq; i++) {
    const h = Math.round(startHour + (i * interval));
    times.push(`${h.toString().padStart(2, '0')}:00`);
  }
  return times;
}

function formatTimeLabel(timeStr: string): string {
  const [h] = timeStr.split(':').map(Number);
  if (h >= 4 && h < 11) return `Pagi (${timeStr})`;
  if (h >= 11 && h < 15) return `Siang (${timeStr})`;
  if (h >= 15 && h < 18) return `Sore (${timeStr})`;
  return `Malam (${timeStr})`;
}

// ─── Google Calendar URL Generator ────────────────────────────

function generateRecurringGCalLink(rem: any, timeSlot: string) {
  const [hours, minutes] = timeSlot.split(':').map(Number);

  const startDate = new Date();
  startDate.setHours(hours, minutes, 0, 0);

  const endDate = new Date(startDate);
  endDate.setMinutes(endDate.getMinutes() + 30);

  const formatUtcStr = (d: Date) => d.toISOString().replace(/-|:|\.\d{3}/g, '');

  const startStr = formatUtcStr(startDate);
  const endStr = formatUtcStr(endDate);

  const title = encodeURIComponent(`💊 Obat: ${rem.medicine}`);
  const details = encodeURIComponent(
    `Jadwal: ${formatTimeLabel(timeSlot)}\nAturan pakai: ${rem.instruction}\nTotal obat: ${rem.qty}\nEstimasi habis: ${rem.days} hari.`
  );

  const recur = `RRULE:FREQ=DAILY;COUNT=${rem.days || 7}`;

  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&dates=${startStr}/${endStr}&details=${details}&recur=${recur}`;
}

// ─── Component ────────────────────────────────────────────────

export function PatientReminderPanel() {
  const [nik, setNik] = useState<string | null>(null);
  const [simrsData, setSimrsData] = useState<any>(null);
  const [loadingSimrs, setLoadingSimrs] = useState(true);
  const [activeReminders, setActiveReminders] = useState<any[]>([]);

  // Parse data obat secara dinamis
  const autoReminders = simrsData?.obat ? simrsData.obat.map((o: any, idx: number) => {
    const schedule = parseFlexibleSchedule(o.waktu);
    const qty = o.qty || 0;
    const days = qty > 0 && schedule.length > 0 ? Math.ceil(qty / schedule.length) : 0;

    return {
      id: `auto-${idx}`,
      medicine: `${o.nama} (${o.dosis})`,
      instruction: o.waktu,
      schedule,
      qty,
      days,
    };
  }) : [];

  // Pengecekan Alarm
  useEffect(() => {
    if (!autoReminders.length) return;

    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    const checkTime = () => {
      const now = new Date();
      const active: any[] = [];

      autoReminders.forEach((rem: any) => {
        rem.schedule.forEach((timeStr: string) => {
          const [schH, schM] = timeStr.split(':').map(Number);
          const schDate = new Date();
          schDate.setHours(schH, schM, 0, 0);
          
          const diffMs = now.getTime() - schDate.getTime();
          const diffMins = Math.floor(diffMs / 60000);

          if (diffMins >= 0 && diffMins <= 30) {
            active.push({ ...rem, dueTime: timeStr });

            if (diffMins === 0) {
              const notifKey = `notif_${rem.id}_${timeStr}_${now.toDateString()}`;
              if (!sessionStorage.getItem(notifKey)) {
                sessionStorage.setItem(notifKey, 'true');
                if ("Notification" in window && Notification.permission === "granted") {
                  new Notification("Waktunya Minum Obat!", {
                    body: `${rem.medicine}\nAturan: ${rem.instruction}`,
                    icon: "/favicon.ico"
                  });
                }
              }
            }
          }
        });
      });

      setActiveReminders(active);
    };

    checkTime();
    const interval = setInterval(checkTime, 30000);
    return () => clearInterval(interval);
  }, [simrsData]);

  // Fetch DB
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem("pharmacy_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.nik) {
          setNik(parsed.nik);
          fetchSimrsData(parsed.nik);
          return;
        }
      }
      setLoadingSimrs(false);
    } catch {
      setLoadingSimrs(false);
    }
  }, []);

  async function fetchSimrsData(userNik: string) {
    try {
      const res = await fetch(`${routes.api.health.replace('/health', '')}/simrs/${userNik}`, {
        headers: getAuthHeader(),
      });
      if (res.ok) {
        const data = await res.json();
        setSimrsData(data);
      } else {
        setSimrsData(null);
      }
    } catch {
      setSimrsData(null);
    } finally {
      setLoadingSimrs(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-10">
      
      {/* HEADER SECTION - Sederhana Sesuai Request */}
      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            Reminder Obat Terintegrasi dengan Google Calendar
          </h1>
        </div>
      </div>

      {/* ACTIVE ALARM BANNER */}
      {activeReminders.length > 0 && (
        <div className="relative animate-in slide-in-from-top-4 fade-in duration-500">
          <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-red-500 to-orange-500 opacity-30 blur animate-pulse"></div>
          <div className="relative flex items-center gap-4 rounded-2xl bg-white p-5 shadow-xl ring-1 ring-red-100">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600">
              <svg className="h-5 w-5 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            <div className="flex-1 flex flex-wrap items-center gap-4">
              <h2 className="font-bold text-slate-800">Waktunya Minum Obat!</h2>
              <div className="flex gap-3 flex-wrap">
                {activeReminders.map((active, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-500"></span>
                    {active.medicine} — {active.instruction}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MAIN CONTENT */}
      {loadingSimrs ? (
        <div className="flex flex-col items-center justify-center space-y-4 py-20">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600"></div>
          <p className="text-sm font-medium text-slate-400 animate-pulse">Menarik data dari Rumah Sakit...</p>
        </div>
      ) : simrsData ? (
        <div className="space-y-4 animate-in fade-in duration-700">
          
          {/* INFO DIAGNOSA - Compact */}
          <div className="flex flex-wrap items-center gap-x-8 gap-y-2 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 uppercase">Diagnosa:</span>
              <span className="font-bold text-slate-800">{simrsData.diagnosa}</span>
            </div>
            {simrsData.tanggal_kunjungan && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-400 uppercase">Kunjungan:</span>
                <span className="font-medium text-slate-700">{simrsData.tanggal_kunjungan}</span>
              </div>
            )}
          </div>

          {/* LIST OBAT - Compact Horizontal Layout */}
          <div>
            {autoReminders.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
                <p className="text-slate-500 font-medium">Tidak ada obat aktif yang diresepkan.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {autoReminders.map((rem: any) => (
                  <div key={rem.id} className="flex flex-col md:flex-row items-center justify-between gap-4 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100 hover:shadow-md transition-shadow">
                    
                    {/* Medicine Info */}
                    <div className="flex-1 w-full md:w-auto flex items-center gap-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 shrink-0">
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-slate-800 leading-tight">{rem.medicine}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm font-medium text-slate-600">{rem.instruction}</span>
                          {rem.days > 0 && (
                            <>
                              <span className="text-slate-300">•</span>
                              <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">Estimasi {rem.days} Hari</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Schedules (Horizontal Buttons) */}
                    <div className="flex flex-wrap items-center justify-end gap-2 w-full md:w-auto">
                      {rem.schedule.map((time: string) => (
                        <a
                          key={time}
                          href={generateRecurringGCalLink(rem, time)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 hover:shadow"
                          title="Simpan ke Kalender"
                        >
                          <svg className="h-3.5 w-3.5 text-blue-500" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20a2 2 0 0 0 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V10h14v10zm0-12H5V6h14v2zm-7 5h5v5h-5v-5z" />
                          </svg>
                          {formatTimeLabel(time).split(' (')[0]} ({time})
                        </a>
                      ))}
                    </div>

                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-2xl bg-white p-12 text-center shadow-sm ring-1 ring-slate-100">
          <div className="mb-3 rounded-full bg-slate-50 p-3">
            <svg className="h-6 w-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h3 className="text-base font-bold text-slate-800">Tidak Ada Resep Aktif</h3>
          <p className="mt-1 text-sm text-slate-500">
            Pengingat obat akan muncul saat Anda memiliki resep dari Rumah Sakit.
          </p>
        </div>
      )}
    </div>
  );
}
