# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.9.45] - 2024-08-15

### Changed

- Read HNO data from global annual dataset(s)

## [0.9.44] - 2024-08-06

### Changed

- Updated BFA operational presence data

## [0.9.43] - 2024-08-01

### Changed

- Updated SDN population data

## [0.9.42] - 2024-08-01

### Changed

- Reenable fuzzy matching

## [0.9.41] - 2024-07-31

### Changed

- Convert xlsx to csv for conflict events

## [0.9.40] - 2024-07-30

### Changed

- Split pipelines test into multiple tests

## [0.9.39] - 2024-07-29

### Fixed

- COD and TCD operational presence update

## [0.9.38] - 2024-07-26

### Fixed

- Honduras operational presence file update

## [0.9.37] - 2024-07-24

### Fixed

- Honduras operational presence file update

## [0.9.36] - 2024-07-19

### Changed

- Refactor org code
- Also add uncleaned names as keys to lookups

## [0.9.35] - 2024-07-18

### Fixed

- Niger operational presence file update

## [0.9.34] - 2024-07-18

### Changed

- Normalise keys in sector and org type lookups on creation
- Fold unofficial mappings into self.data in sector and org type
- Simplify get_code_from_name

## [0.9.33] - 2024-07-17

### Added

- Add 'has_hrp' and 'in_gho' fields to location table

## [0.9.32] - 2024-07-17

### Fixed

- HND population resource names have been updated

## [0.9.31] - 2024-07-15

### Changed

- Update HDX Python Scraper to 2.4.0 - it has a small optimisation to the
filtering and sorting of rows in the RowParser and a larger one which defaults
fill_merged_cells to False so that Frictionless uses OpenPyXL in read only mode

## [0.9.30] - 2024-07-13

### Fixed

- Update filenames for ETH conflict data

## [0.9.29] - 2024-07-12

### Fixed

- Corrected changed Mozambique operational presence parameters

## [0.9.28] - 2024-07-11

### Fixed

- Corrected changed Mozambique operational presence parameters

## [0.9.27] - 2024-07-11

### Changed

- Update Mozambique operational presence data to most recent

## [0.9.26] - 2024-07-10

### Fixed

- Add missing sector mappings in operational presence data

### Changed

- Update Ethiopia operational presence data to most recent

## [0.9.25] - 2024-07-08

### Changed

- get_pcode normalisation improvements

## [0.9.24] - 2024-07-06

### Fixed

- Update filenames for ETH conflict data

## [0.9.23] - 2024-07-05

### Changed

- Use normalise function from HDX Python Utilities
- Update mappings for changes in HDX Python Country

## [0.9.22] - 2024-07-05

### Fixed

- Use latest operational presence data for NER and SDN

## [0.9.21] - 2024-07-05

### Changed

- Added parameter to make phonetic matching optional for org types and sectors
- Added clean_text function to utilities

### Fixed

- Removed outdated error messages from operational presence pipeline

## [0.9.20] - 2024-06-29

### Fixed

- Add check for funding requirements value due to missing data for UKR

## [0.9.19] - 2024-06-25

### Fixed

- Updated Sudan 3W filename

## [0.9.18] - 2024-06-24

### Added

- Specify countries per theme when running via the command line

### Fixed

- Thanks to bugfix in `openpyxl`, added 3W data for: BFA, CAF, COD, NER
- Updated 3W data for: MLI, SOM, ETH, SDN, SSD
- Avoid overwriting orgs with multiple org types

## [0.9.17] - 2024-06-10

### Changed

- Replace "POP" with "all" for humanitarian needs population status

## [0.9.16] - 2024-06-10

### Changed

- Update to latest schema version

## [0.9.15] - 2024-06-05

### Changed

- Switch HNO to use prod HDX data

## [0.9.14] - 2024-06-03

### Added

- Non-standard age categories to population data
- Admin mappings for food prices data

### Changed

- Removed filter on refugee data

### Fixed

- Added missing population data for SLV

## [0.9.13] - 2024-05-30

### Added

- Function to add data to tables in batches

### Changed

- Updated operational presence data for AFG

### Fixed

- Increased speed of conflict event pipeline and included data for all HRP countries

## [0.9.12] - 2024-05-29

### Fixed

- Use schema with fixed enum mappings

## [0.9.11] - 2024-05-29

### Changed

- Roll ups use 'all' instead of '*'

### Removed

- 'unknown' age range

### Fixed

- Replaced line by line commit with batch commit for operational presence and org pipelines

## [0.9.10] - 2024-05-29

### Added

- Missing poverty rate countries: HND, SLV, GTM

## [0.9.9] - 2024-05-28

### Added

- Currencies
- Commodities
- Markets
- Food prices

## [0.9.8] - 2024-05-24

### Fixed

- Temporarily reduce data volume in conflict pipeline

## [0.9.7] - 2024-05-24

### Fixed

- Filter miscoded unit in conflict data
- Correct overwriting issue in conflict pipeline

## [0.9.6] - 2024-05-23

### Added

- Conflict event theme for all HRP countries
- Poverty rate theme for all countries where Oxford MPI is available
- Ability to specify more default parameters in yaml

## [0.9.5] - 2024-05-20

### Added

- Output operational presence errors at end
- Logging functions for consistent output format

## [0.9.4] - 2024-05-17

### Added

- HNO data and tests

## [0.9.3] - 2024-05-16

### Added

- Funding data and tests

## [0.9.2] - 2024-05-15

### Added

- Refugees data and tests
- HXL tag parsing functions to get age and gender

### Changed

- Extended locations to global coverage

## [0.9.1] - 2024-05-14

### Changed

- Don't do phonetic matching for names of 5 characters or less

## [0.9.0] - 2024-05-14

### Changed

- Many changes to align with V1 of the schema

### Removed

- ipc_phase, ipc_type, age_range, gender classes

## [0.8.0] - 2024-05-06

### Changed

- Use hdx id as primary key for resource and dataset tables

## [0.7.9] - 2024-05-04

### Added

- Added hapi_updated_date fields to relevant tables

### Changed

- Updated test data for humanitarian needs theme
- Updated operational presence data for Colombia

## [0.7.8] - 2024-05-01

### Added

- Output views

## [0.7.7] - 2024-04-09

### Removed

- HAPI patch utility

## [0.7.6] - 2024-04-09

### Added

- HAPI patch utility

## [0.7.5] - 2024-04-09

### Changed

- Updated operational presence theme to better match organizations

## [0.7.4] - 2024-04-02

### Added

- Added all HRP countries to operational presence theme

## [0.7.3] - 2024-02-26

### Added

- Added national_risk_view, humanitarian_needs_view, population_group_view,
population_status_view

## [0.7.2] - 2024-02-08

### Added

- Added all HRP countries to food security theme

## [0.7.1] - 2024-02-07

### Added

- Added all HRP countries to national risk theme

### Changed

- Linked national risk to admin 2 level

## [0.7.0] - 2024-01-30

### Added

- Set countries to run for each theme for testing

## [0.6.9] - 2024-01-30

### Changed

- Allow dates to be specified in scraper config

### Added

- Add population data for all HRP countries

## [0.6.8] - 2024-01-23

### Changed

- Change date in org table to match v1 release date
- Correct outdated admin logic in operational presence

## [0.6.7] - 2024-01-17

### Added

- Add national risk AFG, BFA, MLI, NGA, TCD, YEM

## [0.6.6] - 2023-01-08

### Added

- Fix db export (wrong codes being used for age range)

## [0.6.5] - 2023-01-08

### Added

- Fix for humanitarian needs TCD

## [0.6.4] - 2023-11-07

### Added

- Add humanitarian needs AFG, TCD, YEM

## [0.6.3] - 2023-11-07

### Added

- Use better pcode length conversion from HDX Python Country
- Add food security NGA
- When phase population is 0, set population_fraction_in_phase to 0.0

## [0.6.2] - 2023-11-06

### Added

- Org mapping table to deduplicate orgs
- Fuzzy matching for sector and org types

## [0.6.1] - 2023-10-28

### Added

- Limit AdminLevel countries

## [0.6.0] - 2023-10-26

### Added

- Minor unit tests
- Food security and related tables for Burkina Faso, Chad, and Mali

## [0.5.5] - 2023-10-19

### Changed

- Resource filename changed to name

## [0.5.4] - 2023-10-19

### Changed

- HDX provider code and name change

## [0.5.3] - 2023-10-19

### Fixed

- DB export GitHub action pushes to branch db-export

## [0.5.2] - 2023-10-19

### Fixed

- Rename resource "filename" to "name" in metadata

## [0.5.1] - 2023-10-19

### Added

- Default fields for configurations files

## [0.5.0] - 2023-10-16

- Build views in pipeline instead of in hapi-schema

## [0.4.3] - 2023-10-13

### Fixed

- DB Export GitHub action runs on tag push

## [0.4.2] - 2023-10-13

### Added

- Add operational presence code matching to funtion in utilities

## [0.4.2] - 2023-10-12

### Fixed

- Pinned postgres docker image version in DB export GitHub action
- Change sector mapping for erl to ERY

## [0.4.1] - 2023-10-11

### Fixed

- Update requirements to use latest `hapi-schema`
- Change DB export GitHub action to have the HDX API key, and
  to run `pg_dump`  in the postgres docker container

## [0.4.0] - 2023-10-11

### Added

- GitHub Action to create DB export

## [0.3.0] - 2023-10-11

### Added

- Sector and org_type mappings

## [0.2.3] - 2023-10-10

### Fixed

- Remove duplicates from operational presence
- Org type module name from schemas library

## [0.2.2] - 2023-10-06

### Fixed

- Remove HDX link from org

## [0.2.1] - 2023-10-02

### Fixed

- Operational presence resource ref

## [0.2.1] - 2023-10-03

### Added

- Splitting of configs files

## [0.2.0] - 2023-09-29

### Added

- 3W data ingestion
