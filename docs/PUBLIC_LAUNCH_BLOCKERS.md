# Public launch gate

Last reviewed: 11 August 2026.

The product and engineering work below is complete. BetGlitch must still not be
described as a legally finished public service until the owner-supplied facts
and legal review in the final section are complete. Those facts cannot be
inferred safely from source code.

## Closed in code

- [x] The public beta is accountless by default. Registration, login, personal
  dashboard, bankroll, newsletter, pricing and payment entry points are hidden;
  direct page and API access fails closed behind one reversible feature switch.
- [x] Existing account, bankroll, email and payment implementation remains
  dormant rather than being deleted, so a later subscription phase can restore
  it only after its operational and legal prerequisites are complete.

- [x] Account holders can request a one-use, one-hour password-reset link.
  Requests are rate-limited and do not reveal whether an address is registered.
- [x] Authenticated account holders can permanently delete their account after
  password reconfirmation. A matching local newsletter record is deactivated
  and pseudonymized.
- [x] Transactional reset email fails closed when Brevo is not configured.
  Required production variables are documented in
  `docs/RAILWAY_PRODUCTION_ARCHITECTURE.md`.
- [x] The Privacy Policy names the processors actually present in this codebase:
  Railway for hosting and Brevo for transactional/marketing email. It also
  states that no dedicated analytics or error-monitoring service is currently
  enabled.
- [x] The Privacy Policy states the purpose, lawful basis and concrete retention
  behaviour for the personal data the application handles.
- [x] The football/probability provider is described generically. Public vendor
  attribution is deliberately withheld until the contract permits it.
- [x] The database-diagnostics endpoint is no longer publicly routed.
- [x] The temporary public `/test-api` browser diagnostic has been removed.
- [x] Fixture evidence now has an append-only, pre-kickoff context timeline.
  Missing historical observations remain missing rather than being reconstructed.

## Production configuration gate

- [ ] Keep `NEXT_PUBLIC_ACCOUNT_FEATURES_ENABLED=disabled` on both the Railway
  backend and frontend for the accountless public launch.
- [ ] Apply migration `0039_fixturecontextobservation` during the Railway release.
- [ ] Confirm the scheduled evidence sweep calls `/api/internal/evidence/` often
  enough before kickoff to make lineup/context changes useful. The public UI is
  honest when no observations exist, but the feature needs recurring captures.

## Deferred subscription-phase gate

- [ ] Supply the operator/entity, address, jurisdiction and payment-provider
  facts required for a paid customer relationship.
- [ ] Confirm the legal, privacy and support inboxes are actively monitored.
- [ ] Configure and verify Brevo transactional email, including
  `BREVO_SANDBOX_MODE=False`, before restoring registration.
- [ ] Complete payment-provider approval, subscription Terms/Privacy review,
  refund/cancellation handling and an end-to-end checkout test.
- [ ] Only then set `NEXT_PUBLIC_ACCOUNT_FEATURES_ENABLED=enabled`; commerce
  still remains independently fail-closed until commercial mode is enabled.

## Owner and legal gate

- [ ] Supply the exact operating person's or legal entity's name.
- [ ] Supply the registered/service address and country of establishment.
- [ ] Choose the governing law and courts to name in the Terms.
- [ ] Confirm that `legal@betglitch.com`, `privacy@betglitch.com`, and
  `support@betglitch.com` are real, monitored inboxes.
- [ ] Obtain jurisdiction-specific legal review for football-betting content,
  marketing, age gating, responsible-gambling obligations, and the proposed
  Terms/Privacy wording.
- [ ] Confirm contractual permission before naming the football/probability
  vendor publicly or displaying any additional vendor-owned data downstream.

The accountless launch reduces the personal-data and payment surface; it does
not eliminate the need to identify the operator and obtain appropriate review
for a public football-betting information service.
