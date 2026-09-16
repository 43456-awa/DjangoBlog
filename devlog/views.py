from collections import Counter, OrderedDict
from datetime import date, timedelta

from django.shortcuts import render
from django.utils import timezone

from .models import GitCommit


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
    start = today - timedelta(days=today.weekday() + 84)
    daily = Counter()
    for dt in commits.values_list('committed_at', flat=True):
        day = _local_date(dt)
        if day >= start:
            daily[day] += 1

    heatmap = []
    for i in range(91):
        day = start + timedelta(days=i)
        count = daily.get(day, 0)
        heatmap.append({'date': day, 'count': count, 'level': _level(count)})

    groups = OrderedDict()
    for commit in commits[:200]:
        groups.setdefault(_local_date(commit.committed_at), []).append(commit)

    return render(request, 'devlog/changelog.html', {
        'total': total,
        'repo_count': repo_count,
        'week_count': week_count,
        'latest': latest,
        'heatmap': heatmap,
        'groups': groups.items(),
    })
