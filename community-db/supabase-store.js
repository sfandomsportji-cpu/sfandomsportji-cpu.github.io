import {
  validatePostInput,
  validateCommentInput,
  assertCommunityStore
} from './community-store.js';

// Pass an already-created Supabase client into this function.
// Do not hard-code service-role keys or secrets in this repository.
export function createSupabaseCommunityStore(supabase) {
  if (!supabase) throw new Error('SUPABASE_CLIENT_REQUIRED');

  const store = {
    async listPosts({ category, limit = 20, offset = 0 } = {}) {
      const safeLimit = Math.min(Math.max(Number(limit) || 20, 1), 50);
      const safeOffset = Math.max(Number(offset) || 0, 0);

      let query = supabase
        .from('posts')
        .select('id,category,title,body,nickname,created_at,updated_at')
        .eq('status', 'published')
        .order('created_at', { ascending: false })
        .range(safeOffset, safeOffset + safeLimit - 1);

      if (category) query = query.eq('category', category);

      const { data, error } = await query;
      if (error) throw error;
      return data ?? [];
    },

    async createPost(input) {
      const post = validatePostInput(input);

      const { data, error } = await supabase
        .from('posts')
        .insert({
          category: post.category,
          title: post.title,
          body: post.body,
          nickname: post.nickname
        })
        .select('id,category,title,body,nickname,created_at,updated_at')
        .single();

      if (error) throw error;
      return data;
    },

    async listComments(postId) {
      const id = String(postId ?? '').trim();
      if (!id) throw new Error('INVALID_POST_ID');

      const { data, error } = await supabase
        .from('comments')
        .select('id,post_id,body,nickname,created_at,updated_at')
        .eq('post_id', id)
        .eq('status', 'published')
        .order('created_at', { ascending: true });

      if (error) throw error;
      return data ?? [];
    },

    async createComment(input) {
      const comment = validateCommentInput(input);

      const { data, error } = await supabase
        .from('comments')
        .insert({
          post_id: comment.postId,
          body: comment.body,
          nickname: comment.nickname
        })
        .select('id,post_id,body,nickname,created_at,updated_at')
        .single();

      if (error) throw error;
      return data;
    }
  };

  return assertCommunityStore(store);
}
