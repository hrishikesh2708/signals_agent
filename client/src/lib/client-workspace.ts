import { clearProject } from "@/lib/project-storage";
import { clearSession } from "@/lib/session-storage";

/** Drop project + chat session caches (does not clear the auth user blob). */
export function clearClientWorkspace(): void {
  clearProject();
  clearSession();
}
