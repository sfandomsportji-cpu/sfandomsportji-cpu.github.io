// Example only.
// Never commit a service-role key or other secret credential.
//
// For a browser prototype, use only the cloud provider's PUBLIC project URL
// and PUBLIC/ANON client key, protected by database RLS policies.

export const COMMUNITY_CLOUD_CONFIG = {
  provider: 'supabase',
  url: 'https://YOUR_DEV_PROJECT.supabase.co',
  publicAnonKey: 'YOUR_PUBLIC_ANON_KEY'
};
