# BizBoard Group Work Guide

**Assignment 1 – SRS & UML**

Due: 28 November 2026, 22:00 | Maximum 20 pages | Four-person team

## 1. What are we producing?

This assignment is a requirements-and-design report on the topic Business Analytics Application. We are producing a Software Requirements Specification (SRS) and a high-level UML overview for BizBoard, not building or coding the app.

We describe the proposed system clearly enough that a reader can understand what it is intended to do, who will use it, and how its main functions should behave.

## 2. Main capabilities

| Capability | Plain-English explanation |
| --- | --- |
| Dashboards and KPIs | Users choose which important business measurements (KPIs) appear on their dashboard and view them as charts or summary values. |
| Analytics | Users examine performance over time, compare periods or categories, and open more detailed data (drill-down). |
| Reporting | Users create reports for a selected period or topic, schedule recurring reports, and share them with permitted people. |
| Notifications | The system alerts relevant users when a configured unusual condition or important performance update occurs. |
| Collaboration and access | Users share reports with individuals and groups, share a dashboard as a captured screenshot using a button on the main screen, add comments, and access only information they are permitted to see. |

### Project purpose

BizBoard is a web-based business analytics application, accessible on both computers and mobile devices, that helps authorized users monitor business performance in one place. It brings together the company's internal data, such as sales, revenue, customer numbers, and app usage, and presents it through dashboards, KPIs, trend analysis, reports, and alerts. Users can also share reports and dashboards and collaborate within groups, so teams can make faster, better-informed decisions wherever they are.

### KPI names

The dashboard, analytics and reports must use these exact names.

| Group | KPI name | What it shows |
| --- | --- | --- |
| Sales | Total Sales | The number of items or orders sold in the period. |
| Sales | Average Order Value | The average amount spent per order in the period. |
| Revenue | Total Revenue | The total money earned in the period. |
| Revenue | Revenue Growth | How much revenue went up or down compared with another period. |
| Customers | New Customers | The number of customers who joined in the period. |
| Customers | Customer Retention Rate | The share of customers who came back in the period. |
| App usage | Active Users | The number of users who used the app in the period. |
| App usage | Conversion Rate | The share of users who completed a purchase or key action. |

### Market intelligence (optional)

Market intelligence is optional and not compulsory for this assignment. The group may include it only if time allows.

- It would use information from outside the company, such as competitors' pricing, industry and market trends, and customer behavior across the market.
- If included, it would be shown next to the internal BI data so users can compare their own performance with the market.

## 3. What the report should contain

1. Introduction: purpose, scope, definitions and acronyms.
    - Project timeframe and chosen software engineering methodology (optional).
2. Overall description: product perspective, product functions, user classes and characteristics, and constraints.
3. Requirements by feature: for each feature, user stories, use cases, and functional requirements, plus the single overall activity diagram.
4. Non-functional requirements (NFRs).
5. Traceability matrix linking stories, use cases, requirements and acceptance criteria.
6. References in IEEE style.

## 4. How the rubric shapes our effort

**High-mark principle:** every artefact must agree with the others. A feature in a user story should appear in its use case, be supported by one or more functional requirements, and be traceable in the matrix and diagrams.

| Rubric area | Marks | What an excellent result needs |
| --- | --- | --- |
| User stories | 10 | Unique IDs; role, goal and reason; business value; specific, testable acceptance criteria. |
| Use cases | 10 | ID, clear title, actors, preconditions, detailed main flow, relevant alternative flows and postconditions. |
| Functional requirements | 10 | Precise, formal, unique and testable statements in consistent "The system shall..." wording, free from redundancy and ambiguity. |
| Activity diagram | 8 | Correct UML notation (start and end nodes, actions, decisions, forks and joins, swimlanes); covers key workflows; aligns with use cases; comes with a concise description of the flow and decisions. |
| Introduction and overall description | 5 | Clear purpose and scope; coherent product perspective, functions, user types and constraints. |
| Non-functional requirements | 4 | Relevant quality attributes with measurable, realistic and testable targets. |
| Traceability and consistency | 3 | Complete links among user stories, use cases, functional requirements and acceptance criteria or test cases, in both directions (forward and backward) with no gaps. |

## 5. User roles

| Role | What they do |
| --- | --- |
| System Administrator | Manages all groups and permissions across the whole system, manages user accounts including deactivating a user, and can delete any note. |
| Group Owner | Any user who creates a group. Adds and removes members, renames or deletes the group, for that group only. |
| Business User | Monitors KPIs, compares performance, explores data, analyzes trends, generates reports, shares reports and dashboards, opens items shared with them, and writes notes on reports shared through their group. |

## 6. Decisions the group made before detailed writing

| Decision | Team answer |
| --- | --- |
| Concept and name | BizBoard, a web-based business analytics application, accessible on computers and mobile devices, that helps users monitor business performance through dashboards, reports and alerts. |
| Platform | A responsive web application, accessible on both mobile and desktop. Developed mobile first and expanded to desktop later. |
| Data sources | A limited combination of sample datasets and uploaded files. Numbers do not update by themselves: they refresh on a set schedule or when a new file is uploaded. Live connections through APIs are left for a later version. |
| Meaning of real-time | Periodic, not continuous. Dashboard data refreshes every 5 minutes, or right away when a new file is uploaded. After a refresh, the notification reaches the user within 1 minute if there is an alert condition. |
| Anomaly detection | User-defined thresholds. The user sets a rule for a KPI, and an alert is created when the value crosses it. Possible improvement: automatic detection using AI. |
| Sharing model | Reports and dashboard snapshots can be shared with individuals and with groups inside the app. |
| Scope boundaries | Excluded from the first version: live data connections through APIs, automatic anomaly detection using AI, market intelligence (optional), and a dedicated mobile app. |
| ID and document control | IDs (US-01, UC-01, FR-01) are reserved in one shared Google Sheets master list. One team member owns the list and assigns the IDs. Members reserve their IDs there before writing. One team member puts the final report together. |

## 7. Member work allocation

| Member | Work package | Scope |
| --- | --- | --- |
| 1 – Hòa | Dashboard and KPI management | Widget catalogue, saved selection, widget layout, time period. |
| 2 – Len | Business analytics | KPI trend view, period comparison, filtering, drill-down, no-data rule. |
| 3 – Phu | Reporting and notifications | Report generation, report list, report sharing, alert rules, alert checking and delivery, notification settings. |
| 4 – Yuki | Collaboration and access management | Groups, group roles and permissions, report sharing boundaries, report notes, System Administrator. |

## 8. Traceability matrix

### How the team fills it in

1. Add your row as soon as you write a user story. Do not wait until the end.
2. Fill the columns left to right: user story, use case, functional requirements, acceptance criteria, and NFR if one is related.
3. If one story has several use cases or requirements, write them all in the same cell, separated by commas.
4. Each person fills only their own rows. The person who owns the master list checks the whole table.
5. When a requirement changes, update its story, use case, diagram, and row in the same sitting.

| User story | Use case | Functional requirements | Acceptance criteria | NFR (if related) |
| --- | --- | --- | --- | --- |
| US-01 | UC-01 | FR-01, FR-02 | AC-01, AC-02 | NFR-01 |
| US-02 | UC-02 | FR-03 | AC-03 | |
| US-03 | UC-03 | FR-04, FR-05 | AC-04, AC-05 | NFR-02 |
| US-04 | UC-04 | FR-06 | AC-06 | NFR-05 |

### Checks before submitting

- [ ] Every user story appears in at least one row, with a use case, a functional requirement, and an acceptance criterion.
- [ ] Every use case in the use case diagram appears in the matrix.
- [ ] Every functional requirement traces back to a user story (backward check).
- [ ] Every acceptance criterion traces back to a user story and a requirement (backward check).
- [ ] Every NFR listed is tied to the feature it affects, where one applies.
- [ ] No ID appears twice in the master list, and no ID is used in the report that is missing from it.
- [ ] Names of KPIs, roles, and features are spelled the same in the matrix as in the report.

## 9. Member-by-member instructions

### What you should produce

- About 2–3 complete user stories for your package, each with a unique ID, role, goal and reason, business value, and 3–5 specific, testable acceptance criteria.
- A use case for each distinct user goal, with every template field: ID, title, actors, preconditions, main flow, alternative flows, postconditions.
- The functional requirements that satisfy those goals, one behaviour each, in "The system shall..." wording.
- Your main flow, decisions and alternative flows, given to the diagram owner.
- Your IDs, reserved in the shared Google Sheets master list before writing, and your row in the traceability matrix.

### Tips for a strong submission

- Use the shared KPI names and the fixed time periods exactly as agreed, so all four sections stay consistent.
- Write observable acceptance criteria. Avoid words like "user-friendly" or "fast" without a measure.
- Write both sides of every use case: what the user does and what the system displays, validates, saves or returns.
- Cover the no-data case and at least one realistic error in your alternative flows, and say at which step each one branches.
- Stay inside the agreed scope. Anything on the excluded list stays out of your stories, use cases and requirements.
- When something changes, update its story, use case, diagram and matrix row in the same sitting.

### Member 1 – Dashboard and KPI management (Hòa)

**1. Widget catalogue.** A list or picker screen showing the available widgets. A widget is one block on the dashboard that shows one KPI, as a summary number or a chart.

- The user adds or removes widgets by selecting them in the catalogue, which can be a separate screen or a pop-up.
- Each widget has a checkbox. Ticked means it is already on the dashboard, so the same widget cannot be added twice.
- Each widget shows its type, summary value or chart. Optionally it also shows its name, its KPI and a small preview.
- Widgets are grouped by topic: sales, revenue, customers, app usage.
- The user can search the catalogue by widget name.
- The catalogue lists all available widgets. Every user sees the same widgets.
- KPI names must match Member 2's analytics.
- If a widget has no data, the catalogue still shows it, marked as no data, and the dashboard shows the no-data message once it is added.

**2. Saved selection.** The app remembers the widgets the user chose, so the dashboard looks the same next time.

- The selection is personal. Changes do not affect other users.
- It saves when the user taps Save in the catalogue. Nothing changes until then, and closing without saving keeps the previous selection.
- A new user sees a small default set of widgets, so the dashboard is never empty.
- The user can reset to the default set with one action.
- The last chosen time period is saved too, so the dashboard opens the way the user left it.
- If a saved widget is removed from the catalogue or loses its data, the dashboard skips it and shows a short message instead of breaking.
- Because the selection is stored in the database, the user sees the same selection on any device, for example phone and laptop.

**3. Widget layout.** The user arranges widgets, for example by drag and drop, and the layout is restored next time.

- The layout is personal.
- It saves automatically after each move, with no Save button.
- On a phone the user presses and holds to drag. On a computer the user drags with the mouse.
- The user can reset to the default order with one action.
- Removing a widget moves the others up. A new widget appears at the end until moved.
- Storage: the layout is saved in the database, tied to the user's account, in the same place as the saved selection. It follows the user across devices and is not lost when the browser data is cleared.

**4. Time period.** The dashboard shows the selected KPIs for a period chosen from a fixed list.

- The chosen period applies to all KPIs, and the dashboard reloads when it changes.
- The user picks from a menu or a row of buttons at the top of the dashboard.
- The screen always shows the period and its exact dates, for example "Last 7 days: 1 to 7 Nov".
- Periods: Today, Last 7 days, Last 30 days, This month, and Custom range (optional, only if time allows).
- The first time, the dashboard opens on a default such as Last 7 days. After that it opens on the last period chosen.

**5. Dashboard capture and sharing.** The user captures the dashboard as a screenshot and shares it, much like a report.

- A capture button on the main dashboard screen saves the current dashboard as a snapshot. It does not change when live data refreshes.
- The snapshot shows the selected widgets, the period and its exact dates, and the date and time it was captured.
- Each user has a personal dashboard list of the snapshots they captured, plus a separate "Shared with me" section.
- Each item shows the name, the period, and the date and time captured.
- The owner can share a snapshot with individual users and with groups the owner belongs to.
- Recipients can only view it. They cannot edit, delete or re-share it, and there are no comments on dashboards.
- The owner can stop sharing at any time, and the recipient loses access.
- The owner can delete a snapshot, which also removes access for everyone it was shared with.

### Member 2 – Business analytics (Len)

**1. KPI trend view.** The user picks one KPI and sees how it changes over time as a line chart. A trend is how a measure goes up or down over a period.

- The user picks a time range from a fixed list instead of typing dates. The first four match Member 1's periods.
- Today (shown by hour).
- Last 7 days (shown by day).
- Last 30 days (shown by day).
- This month (shown by day).
- Last 3 months (shown by week).
- Custom range (optional, only if time allows).

**2. Period comparison.** The user compares two periods of exactly the same length and chooses both periods.

- The two periods can be from any time, not only the period right before.
- The user first picks the length, for example 7 days, 30 days or one month.
- The user then picks the start date of Period A and of Period B. The system fills in each end date, so both have the same number of days. Example: Period A is 1 to 7 Nov and Period B is 15 to 21 Sep.
- The periods cannot overlap and cannot be the exact same dates. If they are, the system shows a message asking the user to change one.
- The screen shows the exact dates of both periods next to their values.
- The system shows both values side by side, with the difference as a number and as a percentage.
- If one period has no data, the system says so and shows only the other period.

**3. Filtering.** The user narrows results to one slice of the business. Filtering works with the trend view and period comparison, so the chart and numbers update to the chosen slice.

- The user picks a category from a list instead of typing it.
- Categories come from the real data in the sample datasets or uploaded files. The final list is decided once the data is confirmed. Product category, region and sales channel are examples only.
- After choosing a category, the user picks a value, for example Region: North.
- Only categories and values that exist in the data are offered.
- One category filter at a time. Combining several filters is future scope.
- The screen always shows which filter is active.
- The user can clear the filter with one action.
- If no data matches the filter for the chosen period, the system shows a clear empty message instead of a blank chart.

**4. Drill-down.** The user selects a point on a chart, such as one day's revenue, and sees the detailed records behind that number.

- The user taps or clicks a point on the trend chart, for example the bar for 3 Nov.
- The system opens a detail view, as a separate screen or pop-up, listing the records that make up that value, such as individual orders or transactions.
- The detail view shows the selected KPI, the exact date or period, and any active filter.
- The list respects the active filter. With Region: North, only North records are shown.
- The user goes back to the chart with one action, and the chart stays as it was.
- If the point has no detailed records, the system shows a clear empty message.
- Drill-down works on the trend view first. Drilling down from period comparison is a later improvement.

**5. No-data rule.** This applies to all four items above. When there is nothing to show, the system explains why instead of showing a blank screen.

- If no data exists for the chosen period or filter, the system shows a message such as "No data for this period".
- The message says exactly which dates or categories have no data, so the user knows what to upload or select.
- The message shows the period and filter the user selected.
- In period comparison, if only one period has data, the system shows it and states that the other has none.
- The user can change the period or clear the filter directly from the message.
- An empty result is not an error. The system keeps working normally.
- KPI names must match Member 1's dashboard.

### Member 3 – Reporting and notifications (Phu)

#### Reporting

**1. Report generation.** The user picks the KPIs and a time period, and the system creates a PDF report. A report is a snapshot: it records the numbers at the time it was generated and does not change when live data refreshes.

- The user picks one or more KPIs from the shared KPI list.
- The user picks the period from a fixed list matching Member 1's: Today, Last 7 days, Last 30 days, This month, and Custom range (optional).
- The report shows the selected KPIs, the exact dates of the period, and the date and time it was generated.
- The report is a PDF. Other formats, such as CSV, are future scope.
- Every user can select any KPI from the shared list.
- Each report has a name, typed by the user or a default such as "Total Revenue, Last 7 days".

**2. Report list.** Every generated report is saved in a list so the user can open it again.

- The list is personal. Each user sees the reports they created, plus reports shared with them in a separate "Shared with me" section.
- Each item shows the report name, the period, and the date and time it was generated.
- The user can open a report, download the PDF, or delete a report they created.
- Deleting a report also removes access for everyone it was shared with.
- A saved report does not change when data refreshes. For newer numbers, the user generates a new report.

**3. Report sharing.** The owner can share a report with other users. It stays view-only for them.

- Only the owner can share a report.
- The owner can share with a whole group, but only a group the owner belongs to.
- The owner can also share with individual users, including users who share no group with the owner.
- Recipients can open and download the report. They cannot edit, delete or re-share it.
- The report appears in the recipient's "Shared with me" section.
- Each recipient gets a notification in the app and by email, using the same delivery and retry rules as alerts.
- The owner can stop sharing at any time, and the recipient loses access.
- If a recipient leaves the group the report was shared with, they lose access.

**4. Rules for missing or invalid input.** When input is wrong or there is nothing to show, the system explains why instead of failing silently.

- If no KPIs are selected, the system asks the user to choose at least one.
- If the period is invalid, such as an end date before the start date or a date in the future, the system asks the user to fix it.
- If none of the selected KPIs have data, the system shows a no-data message and creates no report.
- If only some KPIs have data, the system shows a confirmation box listing the KPIs with no data. "Generate without them" creates the PDF with only the KPIs that have data. "Cancel" creates nothing and returns to the selection screen. The PDF does not mention the skipped KPIs.
- If building the PDF fails, the system shows an error message, creates no report, and lets the user try again.
- If the owner is in no group, group sharing is unavailable, but sharing with individuals still works.

**5. Scheduled reports.** The user sets a report to be generated automatically on a repeating schedule, such as every Monday at 8 AM.

- The user picks the KPIs, the period, and the frequency, for example weekly or monthly.
- The system generates the PDF on schedule, adds it to the report list, and notifies the user.
- The user can edit or cancel a schedule.
- If a scheduled run fails, the system notifies the user.

#### Notifications

**1. Alert rules.** The user creates a rule that tells BizBoard when to warn them about a KPI. This is a user-defined threshold. Automatic anomaly detection using AI is future scope.

- A rule has three parts: the KPI to watch, the condition ("goes above" or "goes below"), and the number.
- Example: alert me when Total Revenue goes below 1,000.
- The user sets a rule with a simple form: a KPI dropdown, a condition dropdown and a number box, then taps Save. Nothing changes until the user saves.
- Every user can select any KPI from the shared list.
- The number must be valid. If it is empty or not a number, the system asks the user to fix it.
- The user can edit, turn off or delete their own rules.
- Rules are personal and do not affect other users.
- A user can have several rules on the same KPI. Each is checked on its own and can be edited, turned off or deleted without affecting the others.
- Future scope: combining several conditions into one rule.

**2. Alert checking and creation.** After each data refresh, the system checks every active rule against the latest KPI values.

- Data refreshes every 5 minutes, or right away when a new file is uploaded. Rules are checked after each refresh.
- If a KPI crosses the threshold, the system creates one alert for the user who owns that rule.
- The alert shows the KPI name, the condition, the threshold, the actual value, and the date and time.
- While the KPI stays across the threshold, no more alerts are created for that rule. The system remembers whether each rule is currently triggered.
- A new alert is created only after the KPI returns to normal and crosses the threshold again.
- If a rule is turned off and back on, it is treated as new and can alert right away if the KPI is still across the threshold.
- If the KPI has no data after a refresh, the system skips the rule and creates no alert.

**3. Alert delivery.** The alert reaches the user in the app and by email. Push notifications are future scope, because BizBoard is a web app.

- The alert is always saved in the in-app notification list.
- The email is sent within 1 minute after the refresh in which the condition was found.
- The list shows unread alerts first, and the user can mark an alert as read.
- If the email cannot be delivered, the system retries 3 times, 1 minute apart, and stops once an attempt succeeds.
- If every retry fails, the system logs the failure and marks the alert "email not delivered" in the list.
- The 1-minute target applies to the first email attempt. After that, the in-app alert is the guaranteed record.
- The same delivery rules apply when a report is shared with the user.

**4. Notification settings.** Each user controls their own email notifications from their profile page.

- Two separate on-off switches: email when an alert is triggered, and email when a report is shared with the user.
- Both are on by default.
- In-app notifications cannot be turned off.
- If a switch is off, the system sends no email and makes no retries for that type, but the in-app notification still appears.
- If the user has no email address saved, only in-app notifications are sent.
- Turning off a single alert rule is separate from turning off email. A turned-off rule creates no alerts at all.

### Member 4 – Collaboration and access management (Yuki)

**1. Groups.** A group is a set of users who work together and share reports. Any user can create a group and automatically becomes its Group Owner.

- The user creates a group by giving it a name. The Group Owner can rename it later.
- A user can belong to several groups and own several groups.
- The Group Owner adds members directly by searching for a user by name or email. The person is added right away, with no invitation step.
- The Group Owner can remove a member at any time. A removed member loses access to anything shared with that group and can no longer write notes on those reports.
- A member can leave a group at any time.
- A group must always have one Group Owner. To leave, the owner must first hand the group to another member, or delete the group.
- The Group Owner can delete the group. Reports are not deleted. They are no longer shared with that group.
- Future scope: invitations that the person must accept before joining. This needs extra states, such as pending, accepted, declined and expired, plus notifications for each, so it is left out to keep the first version small.

**2. Group roles and permissions.** Inside a group there are two roles. Permissions apply to that group only.

- Member: can open reports shared with the group, write notes on them, and share their own reports with the group.
- Group Owner: can do everything a member can, and can also add or remove members and rename or delete the group.
- The System Administrator sits above all groups (see item 5).
- A user who is not in a group cannot see the group, its members, or what was shared with it.
- If a user without permission tries to open a report or group, the system shows a clear no-access message and nothing else.

**3. Report sharing boundaries.** This sets how Member 3's report sharing connects to groups.

- Any user who creates a report can share it with any individual user in the system.
- The same user can share it with any group they belong to, but not a group they are not in.
- Dashboard snapshots follow the same sharing boundaries: individuals, and groups the owner belongs to. They are view-only, with no notes.
- A recipient who gets a report through a group can read and write notes.
- A recipient who gets a report only as an individual can open it and read the notes, but cannot write notes.
- The owner can stop sharing at any time, and the recipient loses access.

**4. Report notes.** A note is a short text message under a report, working like a small comment thread. The PDF itself never changes.

- Each note shows the author's name and the date and time it was written.
- The report owner can always write notes on their own report.
- Members of a group the report is shared with can write notes on it.
- A person who has the report only as an individual can read notes but cannot write them.
- The author can edit or delete their own notes.
- The report owner can delete any note on their report.
- The System Administrator can delete any note.
- If a user loses access to the report, for example by leaving the group, they can no longer see or write notes on it. Their old notes stay.
- Future scope: annotations pinned to a specific KPI or point inside a report.

**5. System Administrator.** Manages all groups and permissions across the whole system.

- View all groups and their members.
- Add or remove members in any group.
- Change the Group Owner of any group, for example when the owner has left the company.
- Delete any group.
- Delete any note.
- Manage user accounts, including deactivating a user.
- View an activity log of who added or removed members.

## 10. Non-functional requirements

| ID | Quality area | Requirement | Measurement and conditions |
| --- | --- | --- | --- |
| NFR-01 | Performance | Under normal load, 95% of dashboard views shall display their main content within 3 seconds. | Measured on a normal mobile connection using the sample datasets or uploaded files. |
| NFR-02 | Performance | The system shall generate a PDF report within 10 seconds for a typical selection of KPIs and a period of up to 30 days. | Measured from the moment the user confirms until the report appears in the report list. |
| NFR-03 | Performance | The system shall refresh dashboard data every 5 minutes, or right away when a new file is uploaded. | Checked by comparing data timestamps over a 1-hour period. |
| NFR-04 | Performance | The system shall send the alert email within 1 minute after the data refresh in which the alert condition was found. | Measured from the end of the refresh to the first email send attempt. |
| NFR-05 | Security | The system shall deny access to a report, group, or note when the requesting user lacks permission, and shall show a clear no-access message. | Tested by trying to open items without permission, using accounts with different roles. |
| NFR-06 | Security | The system shall require users to sign in before accessing any data, and shall end a session after 30 minutes of inactivity. | Tested by leaving a signed-in session idle for 30 minutes and then trying to open a page. |
| NFR-07 | Security | The system shall use HTTPS for all communication between the browser and the server. | Checked by confirming no page or request is served over plain HTTP. |
| NFR-08 | Security | The system shall store passwords only as salted hashes, never as plain text. | Checked by inspecting the stored user data. |
| NFR-09 | Availability | The system shall achieve 99.5% monthly availability, excluding scheduled maintenance. | Measured as the percentage of successful health checks over a 30-day month. |
| NFR-10 | Reliability | If an alert email cannot be delivered, the system shall retry 3 times, 1 minute apart, and shall always keep the alert in the in-app notification list. | Tested by simulating a mail server failure and checking the retries and the in-app alert. |
| NFR-11 | Reliability | The system shall not lose saved dashboard selections, reports, alert rules, groups, or notes after a restart or failure. | Tested by restarting the system and confirming all saved items are still there. |
| NFR-12 | Compatibility | The interface shall work on the latest two versions of Chrome, Safari, and Edge, on screen widths from 360 pixels (phones) up to desktop sizes. | Tested on each browser at 360 pixels wide and at a standard desktop width. |
| NFR-13 | Usability | A new user shall be able to add a widget to their dashboard within 1 minute without instructions. | Tested by timing at least 5 first-time users on the task. |
| NFR-14 | Usability | All interactive controls on the mobile interface shall be at least 44 by 44 pixels. | Checked by measuring buttons and controls on a 360-pixel-wide screen. |

## 11. How to write each artefact

### A. User stories

Format: As a [user role], I want [goal] so that [reason].

Every story also needs a unique ID such as US-01, a business value explaining why the goal matters, and acceptance criteria with IDs such as AC-01 that can be checked objectively.

- Weak: "As a manager, I want a good dashboard."
- Stronger: "As a Business User, I want to select KPI widgets for my dashboard so that I can focus on the measures relevant to my team."

### B. Use cases

A use case describes the interaction between an actor and the system to achieve a goal. Complete every template field.

| Field | What to write |
| --- | --- |
| Use Case ID and Title | Unique ID (UC-01) and a short verb-based title, for example Generate Report. |
| Actor | The primary actor who starts the goal, plus secondary actors or external systems. |
| Preconditions | What must be true before the use case starts. |
| Main flow | Numbered, chronological steps showing the actor's action and the system's response. |
| Alternative flows | What happens when a decision, error or exception changes the normal path, and the step where it branches. |
| Postconditions | What is true after successful completion. |

Write both sides of the interaction. Include what the system displays, validates, retrieves, saves or returns, not only what the user clicks.

### C. Functional requirements

Format: FR-01: The system shall [one clear behaviour] [under a stated condition, if needed].

- One requirement expresses one main behaviour.
- Make it specific enough to test.
- Use the same terms and roles as the stories and use cases.
- Avoid vague words such as easy, fast, appropriate, user-friendly or efficient unless you define how to measure them.

### D. Non-functional requirements

NFRs describe how well the system must operate. Everyone proposes and reviews them.

| Weak NFR | More testable version |
| --- | --- |
| The dashboard must be fast. | Under normal load, 95% of dashboard views shall display their main content within 3 seconds. |
| The system must be secure. | The system shall deny access to a report when the requesting user lacks permission. |
| The system should be available. | The service shall achieve 99.5% monthly availability, excluding scheduled maintenance. |
| The app should work on phones. | The interface shall work on screen widths from 360 pixels up to desktop sizes. |

### E. UML diagrams

**Use case diagram.** Show the system boundary, the actors outside it, the use cases inside it, and the associations between actors and the goals they take part in.

- Keep names consistent with the written use cases.
- Do not make login or logout the main use cases.

**Activity diagram (8 marks).** The rubric rewards a complete workflow that matches the use cases and uses correct UML notation. We draw one overall activity diagram that combines the major workflows, not a separate diagram for each member.

- Use a clear initial node and final node.
- Use action nodes for activities, and decision and merge nodes for branches.
- Use swimlanes to show responsibility, for example User, BizBoard system, and Email service.
- Show meaningful alternative paths, such as insufficient permission, missing data, report failure, or an alert condition not being met.
- Do not add a workflow that is not in the agreed requirements.

One member assembles the diagram, but every member supplies their workflow and reviews the final diagram against their use cases.

### F. Introduction, overall description, methodology and schedule

- Purpose: state why the SRS is being written and who will use it.
- Scope: state what BizBoard includes and excludes. Do not promise a full enterprise BI replacement.
- Definitions: explain terms such as KPI, BI, dashboard, widget, drill-down, snapshot and SRS.
- Product perspective: explain how BizBoard relates to its data sources and users at a high level.
- Product functions: summarise the main capabilities without repeating every detailed requirement.
- User classes and characteristics: describe each role, its goals and expected technical familiarity.
- Constraints: identify limits such as sample datasets and uploaded files as the only data sources, internet connection, data quality, privacy and security, and supported browsers and screen sizes.
- Methodology and timeframe (optional): briefly name a suitable approach, for example a hybrid of iterative feature work and formal review, and show realistic phases, owners and dates.

## 12. Common mistakes that cost marks

| Avoid this | Do this instead |
| --- | --- |
| Writing only a feature name or a vague story. | Include role, goal, reason, business value and testable acceptance criteria. |
| Writing use cases as a list of button clicks. | Describe actor actions and system responses in a logical sequence. |
| Leaving alternative flows blank. | Consider realistic exceptions and identify the step where each branch starts. |
| Writing requirements such as "the system is user-friendly". | Use one precise "The system shall..." behaviour per requirement. |
| Using NFRs like "fast", "secure" or "reliable" without measures. | Define a metric, target, operating condition and verification method. |
| Adding features that were never agreed. | Keep every artefact inside the agreed scope. |
| Using different names for the same role or feature. | Use the shared KPI names and role names everywhere. |
| Creating diagrams that do not match the written requirements. | Build diagrams from the final use cases and review them against the master list. |
| Filling the report with technical design or code. | Focus on what the system must do and the quality constraints it must meet. |
| Leaving the traceability matrix until the final day. | Update it as IDs and requirements are created. |

## 13. Shared responsibilities (everyone contributes)

- Agree on the concept, scope, actors, terminology and assumptions before writing detailed requirements.
- Review the whole report for consistency, not only your own section.
- Contribute suitable NFR ideas and check that each has a measurable target.
- Provide your story, use case and requirement IDs and links for the traceability matrix.
- Give the diagram owner the main and alternative flows from your feature.
- Check the final document for accuracy, grammar, formatting, references and page limit.

## 14. Final group checklist

- [ ] The group has approved the concept, name, scope, actors and assumptions.
- [ ] The report follows the supplied SRS template and uses consistent terminology.
- [ ] Introduction and overall description cover purpose, scope, perspective, functions, user classes and constraints.
- [ ] Every user story has a unique ID, role-goal-reason statement, business value and testable acceptance criteria.
- [ ] Every use case has an ID, title, actors, preconditions, main flow, alternative flows and postconditions.
- [ ] Functional requirements are unique, precise, testable and use consistent "The system shall..." wording.
- [ ] NFRs cover relevant quality attributes and use realistic measurable targets.
- [ ] Use case diagram actors and use cases match the written requirements.
- [ ] The activity diagram uses correct UML notation and covers the key workflows and decision paths.
- [ ] The traceability matrix links stories, use cases, functional requirements and acceptance criteria without gaps.
- [ ] Methodology and project timeframe are included.
- [ ] References are complete and in IEEE style.
- [ ] The report is professional, proofread and within the 20-page maximum.
- [ ] The Canvas file name follows the convention ISYS3416_A1_[GroupNumber].
- [ ] The original UML diagram or a clear image is attached as a separate file in Canvas, not zipped.
