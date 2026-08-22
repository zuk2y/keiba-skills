# AGENTS.md

このリポジトリ **keiba-skills** は、競馬に関する [Agent Skills](https://agentskills.io) 集（各スキルは `skills/<スキル名>/SKILL.md`）。本ファイルはここで作業するAIエージェント向けの開発ガイドで、[agents.md](https://agents.md/) 標準に準拠する。

人間向けの開発ガイド（リポジトリ概要・[ディレクトリ構成](README.md#ディレクトリ構成)・前提ツール・開発フロー・ローカル検証・スキル追加手順・リリース・コミット/PR 規約）は [`README.md`](README.md#開発) に集約している。作業前に必ず読むこと。

## エージェント向けの注意事項

- ユーザーとのやり取りは日本語で行うこと。
- **コミット前に、変更を stage（`git add`）した状態で人間にレビューを依頼し、承認を得てからコミットすること。** 承認前にコミットしない。
- 変更は原則 `main` に直接コミットする。PR はユーザーが明示的に依頼したときだけ作成する（[README.md の開発フロー](README.md#開発フローpr-は任意)を参照）。
- コミット前に `pipx run pre-commit run --all-files` を実行し、lint／検証を通すこと。
- スキルを追加・変更する場合は [README.md のスキル追加手順](README.md#スキルを追加するとき)に従う。
- コミットメッセージ・PR は [README.md のコミット / PR 規約](README.md#コミット--pr-規約)に従う。
