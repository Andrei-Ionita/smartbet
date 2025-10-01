# SmartBet MVP – 5-Day Sprint (May 10 → May 14 2025)

## Goal
Deliver a bilingual web dashboard **and** Telegram bot for Romanian Liga I bettors, featuring AI-driven 1X2 probabilities.

## Tech stack
- Django 5 • DRF • Celery/Redis
- PostgreSQL
- LightGBM + joblib
- React + Vite + Tailwind + shadcn/ui
- Docker compose; fly.io staging

## Domain model (v0.1)
```mermaid
classDiagram
  Team <-- Match : home_team
  Team <-- Match : away_team
  League <-- Match
  Match <-- OddsSnapshot
  Match <-- Prediction