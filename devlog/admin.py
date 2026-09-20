from django.contrib import admin

from .models import GitCommit


@admin.register(GitCommit)
class GitCommitAdmin(admin.ModelAdmin):
    list_display = (
        'committed_at',
        'display_repo',
        'short_sha',
        'commit_type',
        'summary',
        'branch',
        'is_private',
        'is_public',
        'show_summary',
    )
    list_filter = ('repo', 'is_private', 'is_public', 'show_summary', 'branch')
    search_fields = ('summary', 'sha', 'author', 'repo')
    date_hierarchy = 'committed_at'
    actions = ['hide_selected', 'show_selected']

    @admin.action(description='隐藏所选（不在页面展示）')
    def hide_selected(self, request, queryset):
        queryset.update(is_public=False)

    @admin.action(description='恢复展示所选')
    def show_selected(self, request, queryset):
        queryset.update(is_public=True)
