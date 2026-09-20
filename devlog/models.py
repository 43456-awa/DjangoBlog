from django.db import models


class GitCommit(models.Model):
    """把本地多个仓库的提交同步到数据库，供「开发动态」页面展示。

    隐私策略：来自私有仓库的提交默认只暴露数量与类型，不展示摘要与改动细节，
    后台可逐条放行；同步时命中敏感词的提交会被自动标记为不展示。
    """

    repo = models.CharField('仓库标识', max_length=100, db_index=True)
    repo_label = models.CharField('展示名称', max_length=100, blank=True)
    sha = models.CharField('提交 sha', max_length=40)
    short_sha = models.CharField('短 sha', max_length=12, blank=True)
    branch = models.CharField('分支', max_length=100, blank=True)
    author = models.CharField('作者', max_length=100, blank=True)
    commit_type = models.CharField('类型', max_length=20, blank=True)
    summary = models.CharField('摘要', max_length=300, blank=True)
    committed_at = models.DateTimeField('提交时间', db_index=True)
    files_changed = models.PositiveIntegerField('变更文件数', default=0)
    insertions = models.PositiveIntegerField('新增行', default=0)
    deletions = models.PositiveIntegerField('删除行', default=0)
    is_private = models.BooleanField('来自私有仓库', default=False)
    is_public = models.BooleanField('对外展示', default=True)
    show_summary = models.BooleanField('展示摘要文字', default=True)
    created_at = models.DateTimeField('记录时间', auto_now_add=True)

    class Meta:
        verbose_name = '开发提交'
        verbose_name_plural = '开发提交'
        ordering = ['-committed_at']
        unique_together = ('repo', 'sha')

    def __str__(self):
        return f'{self.display_repo} {self.short_sha}'

    @property
    def display_repo(self):
        return self.repo_label or self.repo

    @property
    def visible_summary(self):
        """页面上真正能显示的摘要；私有仓库或未放行时返回空字符串。"""
        if not self.is_public or not self.show_summary:
            return ''
        return self.summary
