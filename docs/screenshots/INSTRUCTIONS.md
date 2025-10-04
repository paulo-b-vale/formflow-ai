# 📸 Screenshot Instructions

## Where to Place Your Screenshots

Place your application screenshots in this folder (`docs/screenshots/`) with the following names:

### Required Screenshots

1. **dashboard.png** - Main dashboard / home page
   - Show the landing page or main interface
   - Include navigation elements
   - Display key features at a glance

2. **conversation.png** - Conversational interface
   - Show an active conversation with the AI
   - Include multiple messages (user + AI)
   - Demonstrate form filling flow
   - Capture confidence indicators if visible

3. **whatsapp-bot.png** - WhatsApp integration
   - Screenshot of WhatsApp conversation with the bot
   - Show at least 3-4 message exchanges
   - Demonstrate how forms are filled via WhatsApp

4. **analytics.png** - Analytics dashboard
   - Display charts, graphs, or reports
   - Show statistics and metrics
   - Include date ranges and filters

### Optional but Recommended

5. **form-templates.png** - Form template list
6. **user-profile.png** - User profile/settings page
7. **mobile-view.png** - Mobile responsive design
8. **admin-panel.png** - Admin interface (if applicable)

## Screenshot Guidelines

### Technical Requirements

- **Format**: PNG (preferred) or JPG
- **Resolution**: Minimum 1920x1080 (Full HD)
- **Aspect Ratio**: 16:9 preferred
- **File Size**: Keep under 500KB (compress if needed)

### Content Guidelines

**DO**:
- ✅ Use realistic demo data
- ✅ Show complete, functional interfaces
- ✅ Include tooltips/help text if visible
- ✅ Demonstrate key features
- ✅ Use professional-looking sample data
- ✅ Show success states

**DON'T**:
- ❌ Include personal/sensitive information
- ❌ Show error states or broken UI
- ❌ Use lorem ipsum excessively
- ❌ Include browser dev tools
- ❌ Show incomplete features

## How to Take Good Screenshots

### Browser Screenshots

1. **Use Incognito/Private Mode**
   - Clean browser without extensions
   - Consistent appearance

2. **Set Browser Window Size**
   ```javascript
   // In browser console
   window.resizeTo(1920, 1080);
   ```

3. **Tools**:
   - **macOS**: Cmd + Shift + 4
   - **Windows**: Win + Shift + S
   - **Chrome DevTools**: Cmd/Ctrl + Shift + P → "Capture screenshot"
   - **Extensions**: Awesome Screenshot, Fireshot

### WhatsApp Screenshots

1. **Use WhatsApp Web** (web.whatsapp.com)
2. **Zoom out** if needed (Cmd/Ctrl + -)
3. **Crop** to show just the conversation
4. **Hide** phone number/personal info

### Post-Processing

Use tools like:
- **Photoshop/GIMP**: Professional editing
- **TinyPNG**: Compression (tinypng.com)
- **ImageOptim** (macOS): Optimize file size
- **Squoosh** (squoosh.app): Web-based compression

### Adding Annotations (Optional)

If you want to highlight features:
- Use **arrows** or **boxes** to point out key elements
- Add **numbered steps** for tutorials
- Use **consistent colors** (brand colors preferred)

Tools:
- **Skitch** (macOS)
- **Snagit**
- **Greenshot** (Windows)
- **Annotate.net** (web-based)

## Example File Structure

```
docs/screenshots/
├── INSTRUCTIONS.md (this file)
├── dashboard.png
├── conversation.png
├── whatsapp-bot.png
├── analytics.png
├── form-templates.png (optional)
├── mobile-view.png (optional)
└── admin-panel.png (optional)
```

## Sample Data Recommendations

### For Forms
- **Name**: John Silva, Maria Santos, Robert Johnson
- **Email**: john.silva@example.com
- **Location**: Building 2, 3rd Floor - Welding Area
- **Date**: Recent dates (within last week)

### For Analytics
- **Date Range**: Last 30 days
- **Metrics**: Realistic numbers (e.g., 156 submissions, 45 users)
- **Charts**: Show trends with variation

### For Conversations
```
User: "I need to report a workplace incident"
AI: "🟢 I've identified that you want to fill an incident report (95% confidence).
     Let's get started. What is your name?"
User: "John Silva"
AI: "✅ Great! I've saved your name. What's your email address?"
```

## After Adding Screenshots

1. **Verify Links** in README.md work
2. **Check File Sizes** (should load quickly)
3. **Test on GitHub** - push and view the README
4. **Consider Dark Mode** - screenshots look good in both themes?

## Need Help?

- Can't take screenshots? Use placeholder images temporarily
- Need demo data? Check `tests/fixtures/` for sample data
- Questions? Open an issue or discussion

---

**Pro Tip**: Take screenshots of your best UI states after completing a feature, not at the end of the project!
