import os
import re
import subprocess
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand

from devlog.models import GitCommit

SEP = '\x1f'

BOT_PATTERN = re.compile(r'dependabot|copilot|renovate|\[bot\]|noreply@github\.com.*bot', re.I)

SENSITIVE_PATTERNS = [
    re.compile(r'\b\d{1,3}(?:\.\d{1,3}){3}\b'),
    re.compile(r'gh[pous]_[A-Za-z0-9]{16,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{16,}'),
    re.compile(r'\bsk-[A-Za-z0-9]{16,}'),
    re.compile(r'xox[baprs]-[A-Za-z0-9-]{10,}'),
    re.compile(r'BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY'),
]

TYPE_PATTERN = re.compile(r'^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)', re.I)


def parse_type(summary):
    matched = TYPE_PATTERN.match(summary or '')
    return matched.group(1).lower() if matched else ''


def parse_branch(ref_names):
    if '->' in ref_names:
        return ref_names.split('->', 1)[1].split(',')[0].strip()
    return ref_names.split(',')[0].strip() if ref_names.strip() else ''


def is_sensitive(text):
    return any(p.search(text or '') for p in SENSITIVE_PATTERNS)


def parse_datetime(raw):
    """git 的 %aI 带时区，而本项目 USE_TZ=False，统一转成本地朴素时间。"""
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


class Command(BaseCommand):
    help = '把本地多个仓库的提交同步进「开发动态」（幂等，可重复执行）'

    def add_arguments(self, parser):
        parser.add_argument('--repo', help='只同步指定仓库（配置里的 name）')
        parser.add_argument('--since', help='覆盖配置的起始日期，如 2026-09-01')

    def handle(self, *args, **options):
        repos = getattr(settings, 'COMMIT_FEED_REPOS', [])
        if not repos:
            self.stdout.write(self.style.WARNING('settings 里没有配置 COMMIT_FEED_REPOS'))
            return

        only = options.get('repo')
        since_override = options.get('since')
        total_new = 0
        total_seen = 0

        for cfg in repos:
            name = cfg['name']
            if only and only != name:
                continue
            path = cfg['path']
            if not os.path.isdir(path):
                self.stdout.write(f'- {name}: 路径不存在，跳过（{path}）')
                continue

            since = since_override or cfg.get('since') or ''
            branches = cfg.get('branches') or []
            entries = self._read_git_log(path, since, branches)
            new_count = 0
            for entry in entries:
                total_seen += 1
                if self._save(cfg, entry):
                    new_count += 1
            total_new += new_count
            self.stdout.write(
                self.style.SUCCESS(f'- {name}: 读到 {len(entries)} 条，新增 {new_count} 条')
            )

        self.stdout.write(self.style.SUCCESS(f'完成：共扫描 {total_seen} 条，新增 {total_new} 条'))

    def _read_git_log(self, path, since, branches):
        fmt = f'--pretty=format:%H{SEP}%h{SEP}%an{SEP}%aI{SEP}%s{SEP}%D'
        cmd = ['git', '-C', path, 'log', '--no-merges', fmt, '--numstat']
        if since:
            cmd.append(f'--since={since}')
        if branches:
            cmd.extend(branches)
        else:
            cmd.append('--branches')

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180
            )
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f'  git 执行失败: {exc}'))
            return []

        entries = []
        current = None
        for line in proc.stdout.splitlines():
            if SEP in line:
                if current:
                    entries.append(current)
                parts = line.split(SEP)
                current = {
                    'sha': parts[0],
                    'short_sha': parts[1],
                    'author': parts[2],
                    'date': parts[3],
                    'summary': parts[4] if len(parts) > 4 else '',
                    'branch': parse_branch(parts[5]) if len(parts) > 5 else '',
                    'files': 0,
                    'insertions': 0,
                    'deletions': 0,
                }
            elif current and line.strip():
                matched = re.match(r'^(\d+|-)\t(\d+|-)\t', line)
                if matched:
                    current['files'] += 1
                    if matched.group(1) != '-':
                        current['insertions'] += int(matched.group(1))
                    if matched.group(2) != '-':
                        current['deletions'] += int(matched.group(2))
        if current:
            entries.append(current)
        return entries

    def _save(self, cfg, entry):
        if BOT_PATTERN.search(entry['author'] or ''):
            return False
        committed_at = parse_datetime(entry['date'])
        if committed_at is None:
            return False
        summary = (entry['summary'] or '').strip()
        private = bool(cfg.get('private'))
        blocked = is_sensitive(summary)

        defaults = {
            'repo_label': cfg.get('label', cfg['name']),
            'short_sha': entry['short_sha'],
            'branch': entry['branch'],
            'author': entry['author'],
            'commit_type': parse_type(summary),
            'summary': summary[:300],
            'committed_at': committed_at,
            'files_changed': entry['files'],
            'insertions': entry['insertions'],
            'deletions': entry['deletions'],
            'is_private': private,
        }

        obj, created = GitCommit.objects.get_or_create(
            repo=cfg['name'], sha=entry['sha'], defaults=defaults
        )
        if created:
            # 展示 commit 标题本身是允许的（敏感词命中则整条不展示）；
            # 但「改了哪些文件、增删多少行」只对公开仓库显示，见模板
            obj.show_summary = True
            obj.is_public = not blocked
            obj.save(update_fields=['show_summary', 'is_public'])
            return True

        changed = False
        for field, value in defaults.items():
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed = True
        if blocked and obj.is_public:
            obj.is_public = False
            changed = True
        if changed:
            obj.save()
        return False
