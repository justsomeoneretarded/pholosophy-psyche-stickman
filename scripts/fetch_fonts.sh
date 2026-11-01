#!/usr/bin/env bash
# Open-licensed (OFL) fonts from the Google Fonts repository. Missing fonts fall back to system fonts.
set -u
mkdir -p engine/fonts
get() { curl -fsSL --retry 3 "https://raw.githubusercontent.com/google/fonts/main/ofl/$1" -o "engine/fonts/$2" || echo "::warning::font $1 unavailable; using a fallback"; }
get patrickhand/PatrickHand-Regular.ttf hand.ttf
get sharetechmono/ShareTechMono-Regular.ttf digit.ttf

get "nunito/Nunito%5Bwght%5D.ttf" round.ttf
ls -la engine/fonts
