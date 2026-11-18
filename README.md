# Madeira Nightly

An unofficial AltStore and SideStore source for the nightly IPAs from [camhoc/Madeira](https://github.com/camhoc/Madeira/releases).

[![Add source to LiveContainer](https://img.shields.io/badge/Add_source_to-LiveContainer-7057D9?style=for-the-badge)](https://gilma0.github.io/madeira_nightly_ipa_source/?action=livecontainer)
[![Add source to SideStore](https://img.shields.io/badge/Add_source_to-SideStore-1677FF?style=for-the-badge)](https://gilma0.github.io/madeira_nightly_ipa_source/?action=sidestore)

Open either button in Safari on your device, or copy the [source JSON URL](https://gilma0.github.io/madeira_nightly_ipa_source/source.json) into your app's Sources tab.

Madeira requires JIT, and the project recommends iOS 26 or later. Nightly and stable builds share a bundle ID, so switching channels in SideStore can replace an existing Madeira installation. See the [upstream setup instructions](https://github.com/camhoc/Madeira#requirements).

GitHub Actions checks for releases every 15 minutes and publishes the source to GitHub Pages. Downloads come directly from upstream. The generator gets each version and build number from the IPA's Info.plist, which can differ from the release tag. It caches the verified metadata by the IPA's GitHub SHA-256 digest.

To update the source manually, run the **Update and publish source** workflow, or run `python scripts/generate_source.py` locally.
