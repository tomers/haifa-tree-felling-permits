# haifa-tree-felling-permits

## Overview

This repository contains tools to manipulate public data of [tree felling permits by the Haifa municipality](https://www.haifa.muni.il/development-and-construction/engineering-administration/uprooting-trees/). The municipality forest officer is required to pubish this data, as it is public [by law](https://www.gov.il/he/departments/guides/pro_felling_trees).
Unfortunately, for some supposably unexplained reasons, the data is published [as a PDF file](http://www1.haifa.muni.il/trees/rptPirsum.pdf), which is a [non-machine readable format](https://opendatahandbook.org/glossary/en/terms/machine-readable/).

Having non-machine readable format as their sole source of information, is a burden for tree preservation activists. It makes it impossible to track, filter, sort and share the data. It is impossible to integrate the city's data with data of other cities in existing platforms established by forestation activists, such as [meirim.org](https://meirim.org/trees/).

### How it works

The tool in this repository performs the following operations:

- Downloads the [PDF file from the municipality web site](http://www1.haifa.muni.il/trees/rptPirsum.pdf)
- Parses the PDF file using Python's [`pdfplumber` package](https://github.com/jsvine/pdfplumber) into a [Panda's DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)
- Enriches the data by parsing street addresses, normalizing them, and storing its GEO coordinates, using [Google's Geocoding API](https://developers.google.com/maps/documentation/geocoding/overview)
- Stores the data as a [Parquet file](https://arrow.apache.org/docs/python/parquet.html), which is useful for any future data processing
- [Exports the data](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_excel.html) as an Excel spreadsheet (`.xlsx` file)

## Quick Start

```
docker run \
    --rm -t \
    -v $(pwd):/output \
    tomersha/haifa-tree-felling-permits \
    --download
```

Notes:
- Output files will be created in current working directory.

## Local run (development)

Just run `./run.sh`.

## Future Plans

- Integrate with [meirim.org](https://meirim.org/trees/)
- Publish [bubble map](https://www.data-to-viz.com/graph/bubblemap.html) with historical and current data
- Provide web view with sortable table and a map
- Incorporate a tracking mechanism with notification to subscribers, to show and alert of temporal changes - modification to existing permits, or even post-mortem deletion of permits
- Generalize the code to import from other municipalities

## Support

Any feedback and contributions would be highly appreciated. Feel free to contact the maintainer.

## License

Copyright Tomer Shalev, 2022.

Distributed under the terms of the `MIT` license, this code is free and open source software.
