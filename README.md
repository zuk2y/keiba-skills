# keiba-skills

競馬に関する [Agent Skills](https://agentskills.io)（AIエージェント／アシスタント向けの再利用可能なスキル）集。各スキルは `skills/<スキル名>/SKILL.md` に配置（Agent Skills 標準準拠）。

## 収録スキル

| スキル | 概要 |
|---|---|
| [`racehorse-naming-ja`](skills/racehorse-naming-ja/SKILL.md) | 日本の競走馬の馬名を考案（生成）・品評（評価）する。血統・冠名・言語・語感から候補を作り、既存案を登録基準への適合と完成度でグレード評価する。 |

## 導入

### コーディングエージェント（Claude Code / Cursor / Codex / Copilot ほか多数）

[`npx skills`](https://github.com/vercel-labs/skills) で導入：

```bash
npx skills add zuk2y/keiba-skills
# 例: スキルと対象エージェントを指定
npx skills add zuk2y/keiba-skills --skill racehorse-naming-ja -a claude-code -a codex
```

### AIチャット

- **スキル対応チャット（Claude など）**: [Releases](https://github.com/zuk2y/keiba-skills/releases) からスキルの zip をダウンロードしてアップロード。
- **その他のチャット**: [`SKILL.md`](skills/racehorse-naming-ja/SKILL.md) を開き、内容をコピーして指示／プロジェクトに貼り付け。

## リリース／タグ運用

スキルは個別にバージョン管理する。

- タグ形式: **`<スキル名>/v<SemVer>`**（例: `racehorse-naming-ja/v0.2.0`）。版は各 `SKILL.md` の `metadata.version` と一致させる。
- 変更は各スキルの `CHANGELOG.md`（[Keep a Changelog](https://keepachangelog.com/ja/) 形式）に記録する。
- タグを push すると GitHub Actions が該当スキルの zip をビルドし、**CHANGELOG の該当版を本文にした Release** を自動公開する。

```bash
# 版が SKILL.md の frontmatter と一致するか検証してからタグを push
python scripts/release.py racehorse-naming-ja
```

## 開発

開発ガイド（前提ツール・ディレクトリ構成・リリース手順など）は [`AGENTS.md`](AGENTS.md) に集約している。要点のみ以下に記す。

**前提ツール**

- **Python 3.x** — `scripts/*.py` と lint の実行に必要。
- **pipx** — pre-commit / ruff の実行に使う。導入例: `brew install pipx && pipx ensurepath`（macOS）／ `python3 -m pip install --user pipx`（pip 経由）。

**開発フロー（PR ベース）** — `main` への直接 push はしない。変更はブランチ＋Pull Request で入れる。

```bash
git checkout -b docs/xxx        # feat/ fix/ docs/ chore/ を用途で使い分け
# 変更・コミット（pre-commit が整形・検証）
git push -u origin HEAD
gh pr create                    # CI（Lint）が緑になったらマージ
```

**Lint** は pre-commit（ローカル・任意）と GitHub Actions（CI・自動）で走る。ローカルで有効化:

```bash
pipx run pre-commit install           # 以後 git commit 時に自動実行（ruff・整形・スキル検証など）
pipx run pre-commit run --all-files   # 全ファイルに手動実行
```

ruff は pre-commit が自動管理するため個別インストールは不要。スキル単体の検証は `python scripts/lint_skills.py [スキル名]`。
