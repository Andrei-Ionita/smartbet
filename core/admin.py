from django.contrib import admin
from .models import League, Team, Match, OddsSnapshot, MatchScoreModel, MatchMetadata

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name_ro', 'name_en', 'country')
    search_fields = ('name_ro', 'name_en', 'country')

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name_ro', 'name_en', 'slug')
    search_fields = ('name_ro', 'name_en', 'slug')

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'league', 'home_team', 'away_team', 'kickoff', 'status', 'api_ref')
    list_filter = ('league', 'status', 'kickoff')
    search_fields = ('home_team__name_ro', 'away_team__name_ro', 'api_ref')
    raw_id_fields = ('league', 'home_team', 'away_team')

@admin.register(OddsSnapshot)
class OddsSnapshotAdmin(admin.ModelAdmin):
    list_display = ('match', 'bookmaker', 'odds_home', 'odds_draw', 'odds_away', 'fetched_at')
    list_filter = ('bookmaker', 'fetched_at')
    search_fields = ('match__home_team__name_ro', 'match__away_team__name_ro', 'bookmaker')
    raw_id_fields = ('match',)

@admin.register(MatchScoreModel)
class MatchScoreModelAdmin(admin.ModelAdmin):
    list_display = ('match', 'fixture_id', 'predicted_outcome', 'confidence_level', 'recommended_bet', 'generated_at', 'source')
    list_filter = ('predicted_outcome', 'confidence_level', 'source', 'generated_at')
    search_fields = ('match__home_team__name_ro', 'match__away_team__name_ro', 'fixture_id')
    raw_id_fields = ('match',)
    date_hierarchy = 'generated_at'

@admin.register(MatchMetadata)
class MatchMetadataAdmin(admin.ModelAdmin):
    list_display = ('match', 'created_at', 'updated_at')
    search_fields = ('match__home_team__name_ro', 'match__away_team__name_ro')
    raw_id_fields = ('match',)
    date_hierarchy = 'updated_at'
    readonly_fields = ('created_at', 'updated_at')
