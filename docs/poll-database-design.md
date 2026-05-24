# 投票貼文資料庫設計

本文件說明 Easy Social「投票貼文（Poll Post）」功能的資料庫結構，包含資料表、欄位型別、關聯與主要業務規則。

## 設計目標

- 一則貼文（`post`）最多對應一個投票（`poll`）。
- 每個投票包含 2～4 個選項（`poll_option`）。
- 每位使用者對同一則投票只能投 1 票（`poll_vote`）。
- 投票問題文字存放在既有 `post.body` 欄位，與一般文字貼文共用 `post` 表。

## ER 關係圖

```mermaid
erDiagram
    user ||--o{ post : "author_id"
    post ||--o| poll : "post_id (1:1)"
    poll ||--|{ poll_option : "poll_id"
    poll ||--o{ poll_vote : "poll_id"
    poll_option ||--o{ poll_vote : "option_id"
    user ||--o{ poll_vote : "user_id"

    user {
        int id PK
        string username
        string email
    }

    post {
        int id PK
        text body
        int author_id FK
        int repost_of_id FK
    }

    poll {
        int id PK
        int post_id FK UK
        datetime created_at
    }

    poll_option {
        int id PK
        int poll_id FK
        string text
        int position
    }

    poll_vote {
        int id PK
        int poll_id FK
        int option_id FK
        int user_id FK
        datetime created_at
    }
```

## 資料表說明

### 既有表：`post`

投票貼文仍使用 `post` 表儲存，不另建「poll post」專用表。

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | `INTEGER` | PK | 貼文主鍵 |
| `body` | `TEXT` | NOT NULL | 投票問題文字（poll 模式下必填） |
| `media_filename` | `VARCHAR(255)` | NULL | 投票貼文不使用媒體，通常為 NULL |
| `media_type` | `VARCHAR(20)` | NULL | 投票貼文不使用媒體，通常為 NULL |
| `created_at` | `DATETIME(timezone=True)` | NOT NULL, INDEX | 建立時間 |
| `author_id` | `INTEGER` | FK → `user.id`, NOT NULL, INDEX | 作者 |
| `repost_of_id` | `INTEGER` | FK → `post.id`, NULL, INDEX | 轉發來源貼文 |

**與投票的關係：**

- 若 `post` 有對應的 `poll` 列，即為投票貼文。
- 轉發（repost）時，畫面透過 `display_post` 顯示原始貼文內容，投票統計也以**原始貼文**的 `poll` 為準。

---

### 新增表：`poll`

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | `INTEGER` | PK | 投票主鍵 |
| `post_id` | `INTEGER` | FK → `post.id`, NOT NULL, UNIQUE, INDEX | 對應貼文（一對一） |
| `created_at` | `DATETIME(timezone=True)` | NOT NULL | 投票建立時間 |

**關聯：**

- `poll.post_id` → `post.id`（一則貼文最多一個 poll）
- 刪除 `post` 時，cascade 刪除對應 `poll` 及其 options / votes

---

### 新增表：`poll_option`

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | `INTEGER` | PK | 選項主鍵 |
| `poll_id` | `INTEGER` | FK → `poll.id`, NOT NULL, INDEX | 所屬投票 |
| `text` | `VARCHAR(200)` | NOT NULL | 選項文字 |
| `position` | `INTEGER` | NOT NULL | 顯示順序（1～4） |

**約束：**

- `UNIQUE (poll_id, position)`：同一投票內選項順序不可重複

**業務規則（應用層）：**

- 每則投票必須有 **2～4 個**非空選項
- 建立時依 `position` 排序顯示

---

### 新增表：`poll_vote`

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | `INTEGER` | PK | 投票紀錄主鍵 |
| `poll_id` | `INTEGER` | FK → `poll.id`, NOT NULL, INDEX | 所屬投票 |
| `option_id` | `INTEGER` | FK → `poll_option.id`, NOT NULL, INDEX | 使用者選擇的選項 |
| `user_id` | `INTEGER` | FK → `user.id`, NOT NULL, INDEX | 投票使用者 |
| `created_at` | `DATETIME(timezone=True)` | NOT NULL | 投票時間 |

**約束：**

- `UNIQUE (poll_id, user_id)`：同一使用者對同一 poll 只能投 1 票

**業務規則（應用層）：**

- `option_id` 必須屬於同一 `poll_id`
- 未登入使用者不可寫入 `poll_vote`（由路由 `@login_required` 保護）

## 表間關聯摘要

| 父表 | 子表 | 關係 | 外鍵 |
|------|------|------|------|
| `post` | `poll` | 1 : 0..1 | `poll.post_id` |
| `poll` | `poll_option` | 1 : 2..4 | `poll_option.poll_id` |
| `poll` | `poll_vote` | 1 : N | `poll_vote.poll_id` |
| `poll_option` | `poll_vote` | 1 : N | `poll_vote.option_id` |
| `user` | `poll_vote` | 1 : N | `poll_vote.user_id` |

## 主要流程與資料寫入

### 建立投票貼文

1. 新增 `post`（`body` = 投票問題）
2. 新增 `poll`（`post_id` = 新 post）
3. 新增 2～4 筆 `poll_option`

### 使用者投票

1. 查詢 `poll_vote` 是否已有 `(poll_id, user_id)`
2. 若無，新增一筆 `poll_vote`，指向選定的 `poll_option.id`
3. 統計時依 `poll_vote` 聚合各 `option_id` 的票數與百分比

### 統計計算（執行期）

- 總票數 = `COUNT(poll_vote)` where `poll_id = ?`
- 各選項票數 = `COUNT(poll_vote)` group by `option_id`
- 百分比 = `option_votes / total_votes * 100`（總票數為 0 時顯示 0%）

## 實作對應

| 項目 | 位置 |
|------|------|
| ORM Models | `easy_social/models.py` |
| 業務邏輯 | `easy_social/polls.py` |
| 路由 | `easy_social/social.py` |

## 設計取捨

- **為何不把選項存在 JSON 欄位？** 拆成 `poll_option` 表較利於外鍵約束、投票紀錄與統計查詢。
- **為何 `poll_vote` 同時存 `poll_id` 與 `option_id`？** 方便以 `(poll_id, user_id)` 做唯一限制，並快速查詢使用者是否已投票。
- **為何問題文字放在 `post.body`？** 與 Feed、詳情頁、轉發等既有貼文顯示邏輯一致，減少重複欄位。
