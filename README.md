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

このリポジトリで作業する人間・AIエージェント向けの開発ガイド。AIエージェント向けの補足は [`AGENTS.md`](AGENTS.md) を参照（本節をベースに、エージェント固有の注意事項のみ追記している）。

### ディレクトリ構成

- `skills/<name>/` — スキル本体。`SKILL.md`（必須）・`CHANGELOG.md`・`LICENSE`・`NOTICE`。
- `scripts/` — ビルド／リリース／検証スクリプト（Python 統一）。
- `.github/workflows/` — CI（lint）とリリース自動化。

### 前提ツール

- **Python 3.x** — `scripts/*.py` と lint の実行に必要。
- **pipx** — pre-commit / ruff の実行に使う。導入例: `brew install pipx && pipx ensurepath`（macOS）／ `python3 -m pip install --user pipx`（pip 経由）。

### 開発フロー（PR は任意）

個人開発のため PR は必須にしていない。`main` への直接 push を許可しつつ、場面で使い分ける。

- **軽微な変更**（ドキュメント・小さな修正）→ `main` に直接コミット＆push でよい。
- **PR を切ると良い場面**:
  - `@claude` に修正を任せたいとき（PR／Issue 上でのみ起動する）。
  - 大きめ・壊れやすい変更を、CI 緑を確認してから入れたいとき。
  - 変更意図を記録として残したいとき。

PR を使う場合の手順:

1. 作業ブランチを切る（例: `git checkout -b feat/xxx`）。接頭辞は `feat/`（機能）・`fix/`（修正）・`docs/`（文書）・`chore/`（雑務）。
2. 変更してコミット（pre-commit が整形・検証を実行）。
3. push → `gh pr create`。CI（Lint）が緑になったらマージ。

CI（Lint）は push・PR いずれでも走るため、直接 push でも壊れればすぐ気づける。`main` は force push と削除のみ保護している。

### ローカル検証

```bash
pipx run pre-commit install          # 以後 commit 時に自動実行（推奨）
pipx run pre-commit run --all-files  # 全ファイルに手動実行
python scripts/lint_skills.py [スキル名]   # スキル単体の frontmatter + CHANGELOG 検証
```

ruff は pre-commit が自動管理するため個別インストールは不要。直接叩く場合のみ `pipx run ruff check .` / `pipx run ruff format .`。

### スキルを追加するとき

- `skills/<name>/SKILL.md` を作る。`name` はディレクトリ名と一致、小文字・数字・ハイフンのみ、64 文字以内。`description` は 1024 文字以内。`metadata.version` を持たせる。
- `skills/<name>/CHANGELOG.md` を [Keep a Changelog](https://keepachangelog.com/ja/) 形式で作り、`## [<version>]` セクションを用意する（無いとリリースノートが空になり検証で落ちる）。
- ライセンスは `LICENSE` / `NOTICE` を同梱し、frontmatter に `license` を記載。

### コミット / PR 規約

- コミットメッセージは命令形の要約 1 行（英語）＋必要なら本文。
- PR は目的と変更点を簡潔に。関連 Issue があれば紐付ける。
- PR をマージする場合は CI（Lint）が緑であることを条件とする。
