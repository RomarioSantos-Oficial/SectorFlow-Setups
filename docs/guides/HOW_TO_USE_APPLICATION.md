# How to Use the Application

This guide explains the practical step by step workflow for using Sector Flow Setups as an end user.

## 1. What the Application Does

Sector Flow Setups helps you:

1. read Le Mans Ultimate telemetry in real time;
2. understand how the car behaves;
3. get setup suggestions from heuristics and AI;
4. create a new .svm setup without changing the base file;
5. improve suggestions over time from your driving data.

## 2. Before You Start

Make sure:

1. you are on Windows;
2. Python and dependencies are installed;
3. Le Mans Ultimate is installed;
4. Shared Memory is available;
5. you have at least one .svm file to use as a base setup.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

## 3. User Step by Step

### Step 1. Start the application

Run:

```bash
python main.py
```

### Step 2. Wait for game connection

The top indicators show:

- LMU: game connection;
- AI: current AI confidence;
- DB: database status.

### Step 3. Load a base setup

In the Setup tab:

1. click Load .svm;
2. select a setup file;
3. wait for confirmation.

### Step 4. Drive on track

Complete some laps in game. The app collects telemetry while you drive.

### Step 5. Check live telemetry

In the Telemetry tab you can monitor lap times, tyres, fuel, aero, brakes, and weather.

### Step 6. Ask for a suggestion

You can do it in three ways:

1. type in the Setup chat;
2. click Ask AI Suggestion;
3. click Use Heuristics.

Examples:

- the car has understeer on corner entry;
- I need a rain setup;
- rear wing +2;
- tc map -1.

### Step 7. Read the suggestions

Suggestions appear on the right side of the Setup tab with deltas and warnings.

### Step 8. Send detailed feedback

Use the Feedback tab to describe understeer, oversteer, braking, traction, stiffness, and tyre wear.

### Step 9. Create a new setup

1. click Create Setup;
2. choose the mode;
3. choose weather condition;
4. confirm.

The app creates a new .svm file from the base setup.

### Step 10. Edit an existing setup

1. click Edit Setup;
2. pick the .svm file;
3. confirm backup creation;
4. request a suggestion;
5. apply adjustments.

## 4. Language Support

The project already stores a language preference in config, but the GUI text is still hardcoded in Portuguese.

So yes, it is possible to make the app appear in English, Spanish, Japanese, and Chinese, but that language-switching UI is not implemented yet.

What is needed:

1. centralize UI strings;
2. create translation files;
3. add a language selector;
4. reload labels and messages from the selected locale.