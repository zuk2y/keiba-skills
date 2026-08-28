# keiba-skills

競馬に関する [Agent Skills](https://agentskills.io)。各スキルは `skills/<スキル名>/SKILL.md`。

## 収録スキル

| スキル | 概要 |
|---|---|
| [`racehorse-naming-ja`](skills/racehorse-naming-ja/SKILL.md) | 日本の競走馬の馬名を考案・品評する。血統・冠名・言語・語感から候補を作り、既存案を登録基準への適合と完成度でグレード評価する。 |

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
- **その他のチャット**: `skills/<スキル名>/SKILL.md` を開き、内容をコピーして指示／プロジェクトに貼り付け。

## 開発

### ディレクトリ構成

- `skills/<name>/` — スキル本体。`SKILL.md`（必須）・`CHANGELOG.md`・`LICENSE`・`NOTICE`。評価する場合は `evals/`（下記[評価](#評価eval)）。
- `scripts/` — ビルド／リリース／検証スクリプト（Python 統一）。
- `.github/workflows/` — CI（lint）とリリース自動化。

### 前提ツール

- **Python 3.x** — `scripts/*.py` と lint の実行に必要。
- **pipx** — pre-commit / ruff の実行に使う。導入例: `brew install pipx && pipx ensurepath`（macOS）／ `python3 -m pip install --user pipx`（pip 経由）。
- **skill-creator** — スキルの評価に使う。

### 開発フロー（PR は任意）

`main` への直接 push を基本とする。PR を使うかどうかは修正者が判断・明示する。

PR を使う場合の手順:

1. 作業ブランチを切る（例: `git checkout -b feat/xxx`）。接頭辞は `feat/`（機能）・`fix/`（修正）・`docs/`（文書）・`chore/`（雑務）。
2. 変更してコミット（pre-commit が整形・検証を実行）。
3. push → `gh pr create`。CI（Lint）が緑になったらマージ。

CI（Lint）は push・PR いずれでも走る。`main` は force push と削除のみ保護している。

**スキル自体（`skills/<name>/` 配下）の修正を利用者に公開するとき**は、変更が `main` に入ったあと、版を上げてタグを打つ（→ [リリース（版を上げてタグを打つ）](#リリース版を上げてタグを打つ)）。これがタグを打つタイミング。スクリプト・CI・ドキュメントなどリポジトリ運用側だけの変更ではタグは打たない。

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

### 評価（eval）

スキルの **精度** と **トークン量** を計測する。評価エンジンは自前で作らず、Anthropic 公式の
**skill-creator**（Apache-2.0）を土台にする。欲しい比較軸を公式機構がそのまま持つため:

- **スキル有無**（`with_skill/` vs `without_skill/`）・**修正前後**（`skill-snapshot/` ＋ `comparator`/`analyzer` でブラインド比較）
- **精度**（`evals.json` のアサーションを `grader` が採点 → `aggregate_benchmark` が pass_rate 集計）
- **トークン量**（各 run の `total_tokens` を平均±標準偏差で集計）

**前提（必須）**: 評価には **skill-creator の導入が必須**。本リポジトリには eval データ（`evals.json`）しか
置かないため、未導入では実行できない。リポジトリに取り込まず Claude Code のプラグインとして導入する:

```
# 対話セッション（Claude Code CLI）では slash コマンドで
/plugin marketplace add anthropics/skills
/plugin install example-skills@anthropic-agent-skills

# slash が使えない環境（VSCode 拡張・SDK 等）では等価な CLI サブコマンドで
claude plugin marketplace add anthropics/skills
claude plugin install example-skills@anthropic-agent-skills   # 既定 scope=user（リポジトリ外）
```

導入確認は `claude plugin list`。skill-creator は `example-skills` プラグインに含まれる。

**配置**: eval データは公式レイアウトに合わせて `skills/<name>/evals/evals.json` に置く（SKILL.md と同居）。

- 配布物には含めない。`scripts/build.py` はスキルのルート直下 `evals/` を zip から除外する（公式 `package_skill.py` の `ROOT_EXCLUDE_DIRS` に準拠）。
- skill-creator の実行結果（`*-workspace/`・`iteration-*/` 等）は生成物なのでコミットしない（[.gitignore](.gitignore) で除外）。コミットするのは `evals.json` だけ。

### コミット / PR 規約

- コミットメッセージは命令形の要約 1 行（英語）＋必要なら本文。
- PR は目的と変更点を簡潔に。関連 Issue があれば紐付ける。
- PR をマージする場合は CI（Lint）が緑であることを条件とする。

### リリース（版を上げてタグを打つ）

開発フローの最終ステップ。スキルは個別にバージョン管理し、**スキル自体（`skills/<name>/` 配下）の修正を公開するとき**だけ版を上げてタグを打つ。スクリプト・CI・ドキュメントなどリポジトリ運用側だけの変更ではタグは不要。

1. `SKILL.md` の `metadata.version` を上げ、そのスキルの `CHANGELOG.md`（[Keep a Changelog](https://keepachangelog.com/ja/) 形式）に変更を記録する。
2. `python scripts/release.py <スキル名>` を実行する。版が frontmatter と一致するか検証したうえでタグを push する。
3. タグ push を受けて GitHub Actions が該当スキルの zip をビルドし、**CHANGELOG の該当版を本文にした Release** を自動公開する。

タグ形式は **`<スキル名>/v<SemVer>`**（例: `racehorse-naming-ja/v0.2.0`）。版は `SKILL.md` の `metadata.version` と一致させる。
