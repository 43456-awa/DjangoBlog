from collections import Counter, OrderedDict
from datetime import date, datetime, time, timedelta

from django.shortcuts import render
from django.utils import timezone

from blog.models import Article

from .models import GitCommit

HEATMAP_WEEKS = 53
TIMELINE_DAYS = 365
TIMELINE_LIMIT = 600

# 仓库 → 对应文章的标题关键词（用关键词而不是 id，文章重建后依然能对上）
REPO_ARTICLE_KEYWORDS = {
    'auto-eval-app': '青课',
    'doudou-ledger': '豆豆记账',
    'usage-gateway': '用量账簿',
    'automods-lite': '模组工作台',
    'desktop-pet': '桌宠',
}


def _repo_article_map():
    """把仓库名映射到文章对象，页面上项目名就能点进去。"""
    mapping = {}
    for repo, keyword in REPO_ARTICLE_KEYWORDS.items():
        article = (
            Article.objects.filter(status='p', title__contains=keyword).order_by('id').first()
        )
        if article:
            mapping[repo] = article
    return mapping


def _local_date(dt):
    """本项目 USE_TZ=False，库里存的就是本地时间，直接取日期即可。"""
    return dt.date()


def _level(count):
    if count <= 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    return 4


def changelog(request):
    commits = GitCommit.objects.filter(is_public=True).order_by('-committed_at')

    total = commits.count()
    repo_count = commits.values('repo').distinct().count()
    week_count = commits.filter(
        committed_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    latest = commits.first()

    today = date.today()
    start = today - timedelta(days=today.weekday() + (HEATMAP_WEEKS - 1) * 7)
    daily = Counter()
    details = {}
    for commit in commits:
        day = _local_date(commit.committed_at)
        if day >= start:
            daily[day] += 1
            summary = commit.visible_summary
            if summary and len(details.setdefault(day, [])) < 5:
                details[day].append(summary[:60])

    heatmap = []
    for i in range(HEATMAP_WEEKS * 7):
        day = start + timedelta(days=i)
        count = daily.get(day, 0)
        heatmap.append({
            'date': day,
            'count': count,
            'level': _level(count),
            'detail': details.get(day, []),
            'future': day > today,
        })

    cutoff = datetime.combine(today - timedelta(days=TIMELINE_DAYS), time.min)
    timeline = commits.filter(committed_at__gte=cutoff)
    repo_articles = _repo_article_map()
    shown = 0
    groups = OrderedDict()
    for commit in timeline[:TIMELINE_LIMIT]:
        commit.article = repo_articles.get(commit.repo)
        groups.setdefault(_local_date(commit.committed_at), []).append(commit)
        shown += 1

    return render(request, 'devlog/changelog.html', {
        'total': total,
        'repo_count': repo_count,
        'week_count': week_count,
        'latest': latest,
        'heatmap': heatmap,
        'groups': groups.items(),
        'timeline_total': timeline.count(),
        'timeline_shown': shown,
        'timeline_days': TIMELINE_DAYS,
    })
