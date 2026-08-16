import { createClient } from "@supabase/supabase-js";
import { config } from "../config";

export const supabaseAdmin = createClient(config.supabase.url, config.supabase.serviceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});
