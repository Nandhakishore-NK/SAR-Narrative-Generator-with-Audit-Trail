/**
 * SAR Guardian — Supabase Client
 * Configured with project URL and anon key.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://amrkoaquuvscbzmqxgtm.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFtcmtvYXF1dXZzY2J6bXF4Z3RtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE0ODkyMTAsImV4cCI6MjA4NzA2NTIxMH0.PZUu0Enb3oMRIC-CutTrR8TKqmbOcF2GlsN1gcwZtAc";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
