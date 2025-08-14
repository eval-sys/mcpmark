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
            (ref) => `- \`${ref}\`\n  - 拉取: \`docker pull ${ref}\`\n  - 检查: \`docker buildx imagetools inspect ${ref}\``,
          )
          .join('\n')
      : '- 暂无可用标签';

    return [
      COMMENT_IDENTIFIER,
      '### 🐳 Docker 镜像构建完成!',
      '',
      `**Image**: \`${image || 'N/A'}\``,
      `**Version**: \`${version || 'N/A'}\``,
      `**Platforms**: \`${platforms || 'linux/amd64, linux/arm64'}\``,
      `**Build Time**: \`${buildTime}\``,
      '',
      '#### 可用标签与拉取方式',
      pullSection,
      dockerhubUrl ? ['', `🔗 在 Docker Hub 查看所有标签: ${dockerhubUrl}`].join('\n') : '',
      '',
      '> 注意：此构建用于测试与验证。',
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


