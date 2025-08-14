/**
 * Generate or update PR comment with Docker build info
 */
module.exports = async ({ github, context, dockerMetaJson, image, version, dockerhubUrl, platforms }) => {
  const COMMENT_IDENTIFIER = '<!-- DOCKER-BUILD-COMMENT -->';

  const parseTags = () => {
    try {
      if (dockerMetaJson) {
        const parsed = JSON.parse(dockerMetaJson);
        if (Array.isArray(parsed.tags) && parsed.tags.length > 0) {
          return parsed.tags;
        }
      }
    } catch (e) {
      // ignore parsing error, fallback below
    }
    if (image && version) {
      return [`${image}:${version}`];
    }
    return [];
  };

  const generateCommentBody = () => {
    const tags = parseTags();
    const buildTime = new Date().toISOString();

    const pullSection = tags.length
      ? tags
          .map(
            (ref) => `- \`${ref}\`\n  - Pull: \`docker pull ${ref}\`\n  - Inspect: \`docker buildx imagetools inspect ${ref}\``,
          )
          .join('\n')
      : '- No tags available';

    return [
      COMMENT_IDENTIFIER,
      '### 🐳 Docker Build Completed!',
      '',
      `**Image**: \`${image || 'N/A'}\``,
      `**Version**: \`${version || 'N/A'}\``,
      `**Platforms**: \`${platforms || 'linux/amd64, linux/arm64'}\``,
      `**Build Time**: \`${buildTime}\``,
      '',
      '#### Available Tags & Commands',
      pullSection,
      dockerhubUrl ? ['', `🔗 View all tags on Docker Hub: ${dockerhubUrl}`].join('\n') : '',
      '',
      '> Note: This build is for testing and validation purposes.',
    ]
      .filter(Boolean)
      .join('\n');
  };

  const body = generateCommentBody();

  // List comments on the PR
  const { data: comments } = await github.rest.issues.listComments({
    issue_number: context.issue.number,
    owner: context.repo.owner,
    repo: context.repo.repo,
  });

  const existing = comments.find((c) => c.body && c.body.includes(COMMENT_IDENTIFIER));
  if (existing) {
    await github.rest.issues.updateComment({
      comment_id: existing.id,
      owner: context.repo.owner,
      repo: context.repo.repo,
      body,
    });
    return { updated: true, id: existing.id };
  }

  const result = await github.rest.issues.createComment({
    issue_number: context.issue.number,
    owner: context.repo.owner,
    repo: context.repo.repo,
    body,
  });
  return { updated: false, id: result.data.id };
};


