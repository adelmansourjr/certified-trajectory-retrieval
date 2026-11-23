# Data provenance

Ben Williams (2006), *Character Trajectories*, UCI Machine Learning Repository,
[DOI 10.24432/C58G7V](https://doi.org/10.24432/C58G7V).
UCI identifies the original data as CC BY 4.0. All samples are from one writer.

This study downloads the UEA version 3 archive (November 2023), which removes
padding and fixes 39 unequal channel lengths as documented in its README:
https://www.timeseriesclassification.com/aeon-toolkit/CharacterTrajectories.zip

Archive SHA256:
`336f345d6a5280d7e3642978bb8ed85b7e4c6813024d29be157d757cf3c54358`.
The archive is deliberately excluded from version control. The source is credited
here; the downloader verifies its hash and does not silently accept new versions.
Preprocessing interpolates each channel to 48 values and standardizes with official
TRAIN channel statistics. No claim is made that this preserves every original
stroke property or validates vessel-trajectory transfer.
