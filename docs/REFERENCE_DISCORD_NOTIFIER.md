# Reference: High-Fidelity Discord Notification Workflow (v8.2)

This document serves as a standard reference for implementing "Premium" Discord notifications in Python-based analytic pipelines, ensuring visual excellence, zero-intrusiveness, and precise global scheduling.

## 1. Aesthetic & Readability Design (Discord Embeds)

Avoid sending raw text strings. Use **Discord Embeds** to create a structured, professional appearance.

### 1.1 Context-Aware Coloring
Color coding provides instant visual feedback before the user even reads the text.
- **Crisis/Error**: Dark Red (`0x992D22`)
- **Warning/Stress**: Orange (`0xE67E22`)
- **Neutral/Normal**: Blue (`0x3498DB`)
- **Success/Alpha**: Green (`0x2ECC71`)

### 1.2 Structured Fields
Use `inline: true` for compact metric display and `inline: false` for multi-column grouping.
- **Fields**: Use emojis in field names (e.g., `🎯 Target Beta`) to aid scannability.
- **Markdown**: Wrap values in backticks (`` `value` ``) for a monospaced "data-centric" look.

### 1.3 Footer & Metadata
Always include a footer with the system version and source metadata (e.g., Confidence Score, Registry Version) to build trust in the data.

---

## 2. Non-Intrusive Implementation Pattern

The notification logic should be a **side effect**, not a core dependency.

### 2.1 The CLI Flag Pattern
Add a dedicated argument (e.g., `--notify-discord`) to your main entry point. 
- **Decoupling**: The core engine remains blissfully unaware of Discord; only the output layer handles the network request.
- **Safety**: Use a `--no-save` or similar flag if the notification run shouldn't modify the persistent state (database).

```python
# Implementation Example in main.py
if getattr(args, "notify_discord", False):
    from src.output.discord_notifier import send_discord_signal
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
    if webhook_url:
        send_discord_signal(result, webhook_url)
```

---

## 3. GitHub Actions Workflow (Global Scheduling)

Scheduling triggers for specific local times (Paris/Beijing) requires handling UTC offsets and scheduling variance.

### 3.1 UTC Cron Mapping
Since GitHub crons are always UTC, map your local times:
- **14:47 Beijing (CST, UTC+8)** -> `47 06 * * 1-5`
- **17:17 Paris (CET/CEST)** -> `17 15,16 * * 1-5` (Handles DST shift).

### 3.2 The Python Time Window Check
GitHub Actions may trigger +/- 5 minutes off. Use a Python step to check the exact local time using `pytz`.

```yaml
- name: Check Time Window
  id: check
  shell: python
  run: |
    import os, pytz
    from datetime import datetime
    bj_tz = pytz.timezone('Asia/Shanghai')
    now_bj = datetime.now(bj_tz)
    # Check if we are in the target 14:47 window
    is_target = (now_bj.hour == 14 and 40 <= now_bj.minute <= 55)
    should_run = "true" if (is_target or os.environ.get('EVENT') == 'workflow_dispatch') else "false"
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f: f.write(f'should_run={should_run}\n')
```

---

## 4. Configuration & Security

- **Secrets Management**: Store high-sensitivity Webhook URLs in `GITHUB_REPOSITORY_SECRETS`.
- **Environment Variables**: Map secrets to env vars in the workflow step.
- **Rate Limiting**: Use GHA `concurrency` groups to prevent overlapping pushes if the pipeline runs longer than the interval.

---

## 5. Testing & Verification

### 5.1 Local Mock Testing
Create a one-off script (`test_discord.py`) that mocks your `Result` object and calls the notifier directly.
- **Verification**: Check formatting, font size, and color rendering on the mobile/desktop Discord clients.

### 5.2 Manual Trigger
Always include `workflow_dispatch` in your YAML to allow for on-demand verification without waiting for the cron.

---

> [!TIP]
> **Pro-Tip**: Use a custom `avatar_url` and `username` in the Discord payload to give your bot a distinct identity (e.g., "QQQ Monitor AI").
