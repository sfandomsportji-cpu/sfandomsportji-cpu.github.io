// SFANDOM Community Store V1
// Keep the page independent from a specific cloud provider.

export function validatePostInput(input) {
  const title = String(input?.title ?? '').trim();
  const body = String(input?.body ?? '').trim();
  const nickname = String(input?.nickname ?? '').trim();
  const category = String(input?.category ?? 'lounge').trim();

  if (!title || title.length > 120) throw new Error('INVALID_TITLE');
  if (!body || body.length > 5000) throw new Error('INVALID_BODY');
  if (!nickname || nickname.length > 30) throw new Error('INVALID_NICKNAME');
  if (!['nba','football','baseball','lounge'].includes(category)) {
    throw new Error('INVALID_CATEGORY');
  }

  return { title, body, nickname, category };
}

export function validateCommentInput(input) {
  const postId = String(input?.postId ?? '').trim();
  const body = String(input?.body ?? '').trim();
  const nickname = String(input?.nickname ?? '').trim();

  if (!postId) throw new Error('INVALID_POST_ID');
  if (!body || body.length > 2000) throw new Error('INVALID_BODY');
  if (!nickname || nickname.length > 30) throw new Error('INVALID_NICKNAME');

  return { postId, body, nickname };
}

export function assertCommunityStore(store) {
  const required = ['listPosts','createPost','listComments','createComment'];
  for (const name of required) {
    if (typeof store?.[name] !== 'function') {
      throw new Error(`COMMUNITY_STORE_MISSING_${name.toUpperCase()}`);
    }
  }
  return store;
}
