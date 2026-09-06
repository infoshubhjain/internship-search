#!/usr/bin/env python3
"""
Company job boards to search for international internships.

Every token here was probed against the live API and returned jobs; boards
that 404 are not listed, so a 404 at runtime means the company changed or
removed its board rather than a typo here.

These are unauthenticated, documented job-board APIs:
  Greenhouse  https://boards-api.greenhouse.io/v1/boards/<org>/jobs
  Lever       https://api.lever.co/v0/postings/<org>
  Ashby       https://api.ashbyhq.com/posting-api/job-board/<org>

Ashby and Lever return the whole board in one request; Greenhouse needs
?content=true for descriptions, which is a second, larger call made only when
a listing looks relevant.

To add a company: find its board token from any job URL on its careers page
(the path segment after the ATS domain), add it below, and run
`python3 intl_sources.py --check` to confirm it responds.
"""

BOARDS = [
    # ashby
    ('ashby', '1password'),
    ('ashby', 'airbyte'),
    ('ashby', 'baseten'),
    ('ashby', 'browserbase'),
    ('ashby', 'cohere'),
    ('ashby', 'cursor'),
    ('ashby', 'decagon'),
    ('ashby', 'depot'),
    ('ashby', 'elevenlabs'),
    ('ashby', 'granola'),
    ('ashby', 'harvey'),
    ('ashby', 'hex'),
    ('ashby', 'linear'),
    ('ashby', 'mercor'),
    ('ashby', 'modal'),
    ('ashby', 'neon'),
    ('ashby', 'notion'),
    ('ashby', 'omni'),
    ('ashby', 'openai'),
    ('ashby', 'perplexity'),
    ('ashby', 'pika'),
    ('ashby', 'poolside'),
    ('ashby', 'prefect'),
    ('ashby', 'railway'),
    ('ashby', 'ramp'),
    ('ashby', 'render'),
    ('ashby', 'replit'),
    ('ashby', 'sardine'),
    ('ashby', 'sierra'),
    ('ashby', 'supabase'),
    ('ashby', 'synthesia'),
    ('ashby', 'temporal'),
    ('ashby', 'tractable'),
    ('ashby', 'warp'),
    ('ashby', 'wayve'),
    ('ashby', 'zed'),
    # greenhouse
    ('greenhouse', 'adyen'),
    ('greenhouse', 'affirm'),
    ('greenhouse', 'airbnb'),
    ('greenhouse', 'akunacapital'),
    ('greenhouse', 'anthropic'),
    ('greenhouse', 'asana'),
    ('greenhouse', 'celonis'),
    ('greenhouse', 'cloudflare'),
    ('greenhouse', 'cognite'),
    ('greenhouse', 'coinbase'),
    ('greenhouse', 'coupang'),
    ('greenhouse', 'databricks'),
    ('greenhouse', 'datadog'),
    ('greenhouse', 'discord'),
    ('greenhouse', 'dropbox'),
    ('greenhouse', 'elastic'),
    ('greenhouse', 'engineersgate'),
    ('greenhouse', 'faire'),
    ('greenhouse', 'figma'),
    ('greenhouse', 'flowtraders'),
    ('greenhouse', 'getyourguide'),
    ('greenhouse', 'gitlab'),
    ('greenhouse', 'gocardless'),
    ('greenhouse', 'graphcore'),
    ('greenhouse', 'hellofresh'),
    ('greenhouse', 'helsing'),
    ('greenhouse', 'imc'),
    ('greenhouse', 'instacart'),
    ('greenhouse', 'isomorphiclabs'),
    ('greenhouse', 'janestreet'),
    ('greenhouse', 'jumptrading'),
    ('greenhouse', 'mangroup'),
    ('greenhouse', 'mercari'),
    ('greenhouse', 'mongodb'),
    ('greenhouse', 'monzo'),
    ('greenhouse', 'n26'),
    ('greenhouse', 'oldmissioncapital'),
    ('greenhouse', 'proton'),
    ('greenhouse', 'relex'),
    ('greenhouse', 'robinhood'),
    ('greenhouse', 'scaleai'),
    ('greenhouse', 'scandit'),
    ('greenhouse', 'squarepointcapital'),
    ('greenhouse', 'stripe'),
    ('greenhouse', 'truecaller'),
    ('greenhouse', 'twilio'),
    ('greenhouse', 'wise'),
    ('greenhouse', 'wolt'),
    # lever
    ('lever', 'benchsci'),
    ('lever', 'deepgenomics'),
    ('lever', 'matchgroup'),
    ('lever', 'palantir'),]


def board_url(platform, org, content=False):
    """API endpoint listing every job on a board."""
    if platform == 'greenhouse':
        suffix = '?content=true' if content else ''
        return f'https://boards-api.greenhouse.io/v1/boards/{org}/jobs{suffix}'
    if platform == 'lever':
        return f'https://api.lever.co/v0/postings/{org}?mode=json'
    if platform == 'ashby':
        return f'https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true'
    raise ValueError(f'unknown platform: {platform}')
