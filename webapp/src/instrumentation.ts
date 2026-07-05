export async function register(): Promise<void> {
  if (process.env.NODE_ENV !== "production") {
    return;
  }

  // Register production observability integrations here.
}
