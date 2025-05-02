# Supabase Integration for Question Manager

This document explains how to set up and use the Supabase integration for storing and retrieving coding interview questions.

## Setup Instructions

### 1. Create a Supabase Project

1. Sign up at [Supabase](https://supabase.com/) if you don't have an account
2. Create a new project
3. Note your project URL and API key (found in Project Settings > API)

### 2. Set Environment Variables

Create a `.env` file in the root of your project with the following variables:

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-api-key
```

### 3. Create Questions Table

In your Supabase project, create a table called `questions` with the following schema:

| Column Name          | Type      | Description                            |
|----------------------|-----------|----------------------------------------|
| id                   | text      | Primary Key                            |
| title                | text      | Question title                         |
| difficulty           | text      | Difficulty level (easy, medium, hard)  |
| category             | text      | Question category (array, string, etc.)|
| duration_minutes     | integer   | Time limit in minutes                  |
| function_name        | text      | Name of the function to implement      |
| function_signature   | text      | Function signature                     |
| skeleton_code        | text      | Starting code template                 |
| description          | text      | Problem description                    |
| solution_code        | text      | Example solution code                  |
| solution_explanation | text      | Solution explanation                   |
| test_cases           | jsonb     | Test cases as JSON array               |
| hints                | jsonb     | Hints as JSON array                    |
| created_at           | timestamp | Creation timestamp                     |

### 4. Install Required Python Packages

```bash
pip install supabase python-dotenv
```

## Usage

### Importing Questions from CSV

To import questions from a CSV file into Supabase:

```bash
python app/scripts/import_questions_to_supabase.py [path/to/csv_file]
```

If no CSV path is provided, it will use the default `app/testing/create_questions_table.csv`.

### Testing Supabase Connection

To test your Supabase connection and view loaded questions:

```bash
python app/scripts/test_supabase_connection.py
```

## How It Works

1. `DatabaseManager` handles direct interactions with the Supabase API
2. `QuestionManager` uses `DatabaseManager` to load questions
3. If the database connection fails, the system falls back to loading questions from local files

## Code Structure

- **database_manager.py**: Handles Supabase communication
- **question_manager.py**: Manages questions and provides an interface for other components
- **question_models.py**: Defines data models for questions and test cases
- **scripts/**: Utility scripts for importing and testing

## Troubleshooting

- **Connection Issues**: Make sure your environment variables are set correctly and you have an active internet connection
- **Import Errors**: Check that your CSV file has all the required columns
- **Query Errors**: Ensure your Supabase database table schema matches the expected structure 