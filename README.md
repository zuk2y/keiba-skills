# keiba-skills

競馬に関する [Agent Skills](https://agentskills.io)。各スキルは `skills/<スキル名>/SKILL.md`。

## 収録スキル

| スキル | 概要 |
|---|---|
| [`racehorse-naming-ja`](skills/racehorse-naming-ja/SKILL.md) | 日本の競走馬の馬名を考案・品評する。血統・冠名・言語・語感から候補を作り、既存案を登録基準への適合と完成度でグレード評価する。 |

## 位置づけ・免責

- 競馬ファンによる**非公式の個人プロジェクト**で、JRA・NAR・JAIRS・馬主団体・生産者とは関係がない。
- 出力するグレードは**命名の設計を読み解くための参考情報**で、馬名や馬の価値を決めるものではない。実在馬の名はその馬とともにある名として尊重する（既存馬の鑑賞では対案の馬名を出さない設計）。
- **登録の可否を判断するものではない。** 登録基準の記述は特定時点の公表文書を要約したもので、最新の可否は原典と主催者への確認による。
- 最終的な命名は人間が行う。本スキルはその材料を並べるところまでを担う。

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

- `skills/<name>/` — スキル本体。`SKILL.md`（必須）・`CHANGELOG.md`・`LICENSE`・`NOTICE`。評価する場合は `evals/`（下記[評価](#評価eval)）。スキル固有のエージェント指針があれば `AGENTS.md`（＋Claude Code 用に `@AGENTS.md` を書いた `CLAUDE.md`）を置く。これらは開発用のため配布 zip からは除外される。
- `evals/<name>/` — `claude plugin eval` が読むケース（`evals.json` から `scripts/gen_plugin_evals.py` で生成）。`evals/results/` は実行結果で gitignore 済み。root の `.claude-plugin/plugin.json` は評価のために `skills/` 配下をプラグインとして束ねる manifest で、配布物には影響しない。
- `scripts/` — ビルド／リリース／検証スクリプト（Python 統一）。
- `.github/workflows/` — CI（lint）とリリース自動化。

### 前提ツール

- **Python 3.x** — `scripts/*.py` と lint の実行に必要。
- **pipx** — pre-commit / ruff の実行に使う。導入例: `brew install pipx && pipx ensurepath`（macOS）／ `python3 -m pip install --user pipx`（pip 経由）。
- **Claude Code v2.1.269 以降** — `claude plugin eval` でスキルを評価する（`claude --version` で確認、`claude update` で更新）。

### 開発フロー（PR は任意）

`main` への直接 push を基本とする。PR を使うかどうかは修正者が判断・明示する。ただし[クラウドセッション](#作業環境ローカル--クラウドセッション)からの変更は、指定された作業ブランチにしか push できないため **PR を基本**とする。

PR を使う場合の手順:

1. 作業ブランチを切る（例: `git checkout -b feat/xxx`）。接頭辞は `feat/`（機能）・`fix/`（修正）・`docs/`（文書）・`chore/`（雑務）。
2. 変更してコミット（pre-commit が整形・検証を実行）。
3. push → `gh pr create`。CI（Lint）が緑になったらマージ。

CI（Lint）は push・PR いずれでも走る。`main` は force push と削除のみ保護している。

**スキル自体（`skills/<name>/` 配下）の修正を利用者に公開するとき**は、変更が `main` に入ったあと、版を上げてタグを打つ（→ [リリース（版を上げてタグを打つ）](#リリース版を上げてタグを打つ)）。これがタグを打つタイミング。スクリプト・CI・ドキュメントなどリポジトリ運用側だけの変更ではタグは打たない。

### 作業環境（ローカル / クラウドセッション）

このリポジトリは、手元の PC（各自の git 資格情報で操作する環境。Claude Code CLI などのエージェントを含む）でも、[Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web) のクラウドセッションでも開発できる。ただし**クラウドセッションは GitHub App として push する**ため、次の3つができない（いずれも GitHub が 403 で拒否する）。

| 操作 | クラウドセッション | 手元の PC |
|---|---|---|
| ブランチへの push・PR 作成 | ○ | ○ |
| **タグ ref の作成・push** | ✗ | ○ |
| **`.github/workflows/` 配下の変更の push** | ✗（`workflows` 権限がない） | ○ |
| **ワークフローの API 起動（`workflow_dispatch`）** | ✗（`Actions: write` がない） | ○（ブラウザの Run workflow でも可） |

App が要求する権限はアプリ側が定義しており利用者側で追加できないため、上記はクラウドセッション側の設定では解消できない。運用としてはこう分担する。

- **通常の変更**（スキル本文・スクリプト・ドキュメント）: どちらでも可。ただしクラウドセッションは指定された作業ブランチにしか push できないため、**PR を作り、マージは人間が行う**。
- **ワークフローの変更**: 手元の PC からコミットする。クラウドセッションで編集した場合は、ファイルを受け取って手元で適用する。
- **リリース**: 手元から `scripts/release.py`、またはブラウザで Actions → Release → *Run workflow*（→ [リリース](#リリース版を上げてタグを打つ)）。後者はタグ push を伴わないため、クラウドセッションで作業した流れのままブラウザだけで完結できる。

### ローカル検証

```bash
pipx run pre-commit install          # 以後 commit 時に自動実行（推奨）
pipx run pre-commit run --all-files  # 全ファイルに手動実行
python scripts/lint_skills.py [スキル名]   # スキル単体の frontmatter + CHANGELOG + evals 検証
```

ruff は pre-commit が自動管理するため個別インストールは不要。直接叩く場合のみ `pipx run ruff check .` / `pipx run ruff format .`。

### スキルを追加するとき

- `skills/<name>/SKILL.md` を作る。`name` はディレクトリ名と一致、小文字・数字・ハイフンのみ、64 文字以内。`description` は 1024 文字以内。`metadata.version` を持たせる。
- `skills/<name>/CHANGELOG.md` を [Keep a Changelog](https://keepachangelog.com/ja/) 形式で作り、`## [<version>]` セクションを用意する（無いとリリースノートが空になり検証で落ちる）。
- ライセンスは `LICENSE` / `NOTICE` を同梱し、frontmatter に `license` を記載。

### 評価（eval）

スキルの **精度** と **費用** を計測する。評価エンジンは自前で作らず、Claude Code 公式の
[`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) で回す。ケースの正本は skill-creator 互換の
`skills/<name>/evals/evals.json` に置き、ランナーが読む形式（`evals/<name>/<NN-ケース名>/prompt.md` ＋
`graders/*.md`）は `scripts/gen_plugin_evals.py` で生成する。

**前提**: Claude Code v2.1.269 以降と、普段のセッションと同じ認証（実行と採点はその利用枠／API 課金に乗る）。

**流れ**:

1. `evals.json` を編集したら `python3 scripts/gen_plugin_evals.py` で生成し直す（pre-commit が `--check` で食い違いを検出する）。
2. リポジトリ root で回す。初回は「Trust this plugin directory?」に y と答える。

   ```bash
   # 1 ケースだけ・1 回・対照なし（ケースや採点基準を調整するとき）
   claude plugin eval . --case "12-*" --runs 1 --ablation none --allow-tools WebSearch --judge-model sonnet --no-publish
   # モードで絞る（generate / critique）
   claude plugin eval . --tag critique --ablation none --allow-tools WebSearch --judge-model sonnet -j 4 --max-cost-usd 20
   # 全ケース（費用上限つき、JSON も残す）
   claude plugin eval . --ablation none --allow-tools WebSearch --judge-model sonnet -j 4 --max-cost-usd 60 --json evals/results/latest.json
   ```

3. 結果は `evals/results/<timestamp>/` の `aggregate-result.json` と `report.html`（自己完結の HTML。ジャッジの票と根拠まで見える）。

**費用を抑える設計**（生成スクリプトの定数と実行フラグに対応）:

- 実行は MCP・CLAUDE.md・個人設定を載せない隔離セッション。固定文脈はサブエージェント方式（約 37k tokens）の半分程度で、毎ターンの読み直しがその分減る。
- 各ケース `runs: 1`・`max_turns: 40`・`timeout_seconds: 1200`。結果が割れるケースだけ `--runs 3` で回す。暴走は `--max-cost-usd` で止める。
- `--ablation none` で「スキル無し」対照を省く（既定の with-without は倍の費用。description の発火確認や有無比較のときだけ既定で回す）。
- 採点は各アサーションを 1 つの `llm` grader（3 票の多数決）にし、`skill-fired` grader でスキルの発火を記録する。ジャッジは `--judge-model sonnet` を指定する（既定の小型モデルは日本語の否定型「〜が漏れていない」を逆に読んで FAIL にすることがあった。ジャッジ費用は実行費用の数％なので Sonnet でも軽い）。
- ツールは WebSearch のみ。WebFetch は 1 回 3〜10k tokens を文脈に足すので評価では許可しない（SKILL.md は「一般的なウェブ検索で照合」としており仕様に反しない）。
- `append_system_prompt` で指示するのは「回答は最終メッセージに全文を書く」「独立した検索は 1 ターンに並列発行する」だけ（判定や手順には触れない）。

**比較軸**:

- **修正前後**: 修正の前後で同じコマンドを回し、`aggregate-result.json` の `cases[].aggregates.score` と `graders` の verdict を突き合わせる。
- **スキル有無**: `--ablation with-without`（既定）で `Δ` を見る。
- **費用**: JSON の `costUsd`（定価換算、ジャッジ込み）と `durationSeconds`。トークン内訳が要るときは `--keep-temp` で残る `trace.jsonl` の `usage` を集計する。

**品評ケースのメタデータ**: 品評ケース（`"mode": "品評"`）は期待する採点を機械可読な形で持ち、`scripts/lint_skills.py` が SKILL.md の「土台グレード」表と突き合わせて自己矛盾（記号と帯の食い違い）を検出する。

| フィールド | 内容 |
|---|---|
| `target_grade_band` | 期待する総合グレード帯。`S+`/`S`/`A`/`B`/`C`/`不可`。幅を持たせるなら `A〜S` |
| `target_symbols` | 土台3軸の記号 `{"連想": …, "言語一致": …, "背景": …}`。値は `—`/`△`/`○`/`◎`/`◉`、範囲は `○〜◎` |
| `target_band_shift` | 副次パーフェクト昇格 `+1`・制約違反による減格 `-1` などの段数（省略時 0） |
| `target_note` | 自由記述（そのケースの狙い・補足） |

- 検証は「記号から採点表が導く帯が `target_grade_band` に収まるか」。導かれる帯を含んでいれば通る（記号が `B` を導くとき `C〜B` は可）。
- `target_grade_band`・`target_symbols`・`target_note` は品評ケースの必須。固定しないケース（登録可否が主眼・記号が開くなど）は値に `null` を明示する。
- `不可`（Mゲートの確定却下）は採点に進まないので記号を持たない。
- 採点表は SKILL.md から読むため、表を改訂すれば検証もそのまま追随する（表の書式を変えると lint が落ちて突き合わせを促す）。

### コミット / PR 規約

- コミットメッセージは命令形の要約 1 行（英語）＋必要なら本文。
- PR は目的と変更点を簡潔に。関連 Issue があれば紐付ける。
- PR をマージする場合は CI（Lint）が緑であることを条件とする。

### リリース（版を上げてタグを打つ）

開発フローの最終ステップ。スキルは個別にバージョン管理し、**スキル自体（`skills/<name>/` 配下）の修正を公開するとき**だけ版を上げてタグを打つ。スクリプト・CI・ドキュメントなどリポジトリ運用側だけの変更ではタグは不要。

1. `SKILL.md` の `metadata.version` を上げ、そのスキルの `CHANGELOG.md`（[Keep a Changelog](https://keepachangelog.com/ja/) 形式）に変更を記録する。変更を `main` に入れる。
2. リリースを起動する。次のどちらでもよい。
   - **ローカルから**: `python scripts/release.py <スキル名>` を実行する。版が frontmatter と一致するか検証したうえでタグを push する。
   - **GitHub 上から**（タグを push できない[クラウドセッション](#作業環境ローカル--クラウドセッション)向け）: Actions → **Release** → *Run workflow* でスキル名を入力して実行する（`workflow_dispatch`。API からも起動できる）。ワークフローが `SKILL.md` の `metadata.version` を読んでタグを作成するので、手元でタグを打つ必要がない。この起動口はワークフロー定義が `main` にある場合のみ表示される。
3. いずれの場合も GitHub Actions が該当スキルの zip をビルドし、**CHANGELOG の該当版を本文にした Release** を自動公開する。

タグ形式は **`<スキル名>/v<SemVer>`**（例: `racehorse-naming-ja/v0.2.0`）。版は `SKILL.md` の `metadata.version` と一致させる（ワークフローは公開前にこの一致と CHANGELOG の該当節を検証し、合わなければ落とす）。
