# -*- coding: utf-8 -*-

import math
from webapi import strutils
import webapi.spheres.hotels as hotels
from webapi.estools import utils
from webapi.extractor import MoviesExtractor, HotelsExtractor, \
    RestaurantsExtractor

SPHERE = {hotels.NAME,
          "movies"}

SPHERE_SCHEMA_MAP = {"kidsgoods": "kids_goods",
                     "peoplelarge": "people_large"}

# Sphere name -> sphere label map
SPHERE_LANG = {hotels.NAME: {"en": "Hotels", "ru": "Отели"},
               "movies": {"en": "Movies", "ru": "Фильмы"}}

SPHERE_CAT_TRANS = {"electronics": {"en": "Electronics", "ru": "Техника"},
                    "clothing": {"en": "Clothing", "ru": "Одежда"},
                    "computers": {"en": "Computers", "ru": "Компьютеры"},
                    "kidsgoods": {"en": "Kids Goods", "ru": "Детские товары"},
                    "books": {"en": "Books", "ru": "Книги"}}


# Sphere name -> categories map
SPHERE_GROUP_CATEGORY_MAP = {}

# Supported languages
LANG = {"en", "ru"}

SPHERE_FILTERS = {
    hotels.NAME: {
        "country": {"type": "term"},
        "location": {"type": "term"},
        "admin1": {"type": "term"},
        "city": {"type": "term"},
        "stars": {"type": "range"},
        "price_range": {"type": "range"},
        "amenities": {"type": "bool-list"}
        # "catalog": {"type": "catalog"}  # TODO Hack
    },
    "movies": {
        "genres": {"type": "bool-list"},
        "creators": {"type": "bool-list"},
        "actors": {"type": "bool-list"},
        "directors": {"type": "bool-list"},
        "years": {"type": "range"},
        "countries": {"type": "bool-list"},
        "producers": {"type": "bool-list"},
        "writers": {"type": "bool-list"}
    }}

SPHERE_CATALOGS = {hotels.NAME:
                       {"levels": [
                           ("location_tree", "country"),
                           ("location_tree", "admin1"),
                           ("location_tree", "city")]}}

SPHERE_DATA_FIELDS = {}


# TODO Move to some helper class
def _name_ixd(name, fields):
    for i, f in enumerate(fields):
        if f["name"] == name:
            return i

    raise Exception("name not found")


# TODO To be moved to dicts or somewhere else
def simple_transformer(sphere, index, row, lst, field, fields):
    idx = _name_ixd(field["name"], fields)

    input = strutils.build_input(row[idx])
    a = utils.to_action(index, "dict", input, input, row[idx].strip(),
                        {"name": strutils.to_name(row[idx])})
    lst[strutils.to_name(row[idx])] = a


def default_conv(val):
    return strutils.to_name(val)


def float_floor_conv(val):
    if not val:
        return 0
    float_val = float(val)
    return math.floor(float_val)


def int_conv(val):
    if not val:
        return 0
    int_val = int(val)
    return int_val


def director_list_conv(lst):
    if not lst:
        return []
    return [strutils.to_name(s["name"]) for s in lst]


def list_conv(lst):
    if not lst:
        return []
    return [strutils.to_name(s) for s in lst]


def country_conv(lst):
    if not lst:
        return []
    return [strutils.to_name(s["country"]) for s in lst if s.get("country")]


def uniq_id(vals):
    return "".join(vals)


def location_transformer(sphere, index, row, lst, field, fields):
    val = by_path(row, "location", field.get("json"))

    if not val:
        return

    input = strutils.build_input(val)
    a = utils.to_action(index, "dict", input, input, val.strip(),
                        {"name": strutils.to_name(val),
                         "country": by_path(row, "country",
                                            ["data", "location_tree"])})
    lst[strutils.to_name(val)] = a


def name_transformer(sphere, index, row, lst, field, fields):
    idx = field["name"]
    if not row.get(idx):
        return
    inval = strutils.build_input(row[idx])
    a = utils.to_action(index, "dict", inval, inval, row[idx].strip(),
                        {"id": row["_id"],
                         "name": strutils.to_name(row[idx])})
    lst[strutils.to_name(row[idx])] = a

def object_rating(sphere, index, row, lst, field, fields):
    src = {}
    for field in fields:
        fname = field["name"]
        path = field.get("json")
        if fname in ["_id", "name"]:
            continue

        if fname == "criteria" and row.get(fname):
            val = row[fname]
            for k in val:
                #if k["criterion_id"] == sphere.default_criterion:
                    #src["default"] = k["norm_score"]
                src[k["criterion_id"]] = k["norm_score"]
        elif fname != "criteria":
            conv = field.get("convert", default_conv)
            if path:
                val = by_path(row, fname, field.get("json"))
            else:
                val = row[fname]
            if field.get("filter_name"):
                src["_" + field["filter_name"]] = conv(val)
            else:
                src["_" + fname] = conv(val)

    if sphere.default_criterion not in src:
        src[sphere.default_criterion] = None

    d = {"_index": index,
         "_type": "rating",
         "_id": row["_id"],
         "_source": src}

    lst.append(d)


def country_transformer(sphere, index, row, lst, field, fields):
    val = by_path(row, "country", field.get("json"))

    nval = strutils.to_name(val)
    if not nval:
        return
    input = strutils.build_input(val)

    a = utils.to_action(index, "dict", nval, input, val.strip(),
                        {"name": nval,
                         "path": [nval, "", ""]})

    # only unique values must be appended
    uid = uniq_id([val])
    if uid not in lst:
        lst[uid] = a


def admin1_transformer(sphere, index, row, lst, field, fields):
    val = by_path(row, "admin1", field.get("json"))

    if not val:
        return

    admin1 = strutils.to_name(val)
    country = strutils.to_name(by_path(row, "country", field.get("json")))
    input = strutils.build_input(val)
    a = utils.to_action(index, "dict", admin1, input, val.strip(),
                        {"name": admin1,
                         "path": [country,
                                  admin1,
                                  ""]})

    uid = uniq_id([country if country else "", admin1 if admin1 else ""])
    if uid not in lst:
        lst[uid] = a


def city_transformer(sphere, index, row, lst, field, fields):
    val = by_path(row, "city", field.get("json"))

    input = strutils.build_input(val)
    city = strutils.to_name(val)
    if not city:
        return

    country = strutils.to_name(by_path(row, "country", field.get("json")))
    admin1 = strutils.to_name(by_path(row, "admin1", field.get("json")))
    a = utils.to_action(index, "dict", city, input, val.strip(),
                        {"name": city,
                         "path": [country,
                                  admin1,
                                  city]})

    uid = uniq_id([country if country else "", admin1 if admin1 else "",
                   city if city else ""])
    if uid not in lst:
        lst[uid] = a


def get_from_dict(data, lst):
    from functools import reduce

    return reduce(lambda d, k: d.get(k, {}), lst, data)


def by_path(row, fname, path):
    if path:
        val = get_from_dict(row, path)
        val = val.get(fname)
    else:
        val = row.get(fname)
    return val


def list_transformer(sphere, index, row, lst, field, fields):
    fname = field["name"]
    val = by_path(row, fname, field.get("json"))

    if not val:
        return

    for item in val:
        a = utils.to_action(index, "dict", strutils.to_name(item),
                            strutils.build_input(item), item,
                            {"label": item,
                             "name": strutils.to_name(item)})

        uid = uniq_id([strutils.to_name(item)])
        if uid not in lst:
            lst[uid] = a


def people_transformer(sphere, index, row, acc, field, fields):
    fname = field["name"]
    val = by_path(row, fname, field.get("json"))

    if not val:
        return

    for item in val:
        name = item["name"]
        uid = uniq_id([strutils.to_name(name)])
        if uid not in acc:
            inval = strutils.build_perms(name)
            a = utils.to_action(index, "dict", strutils.to_name(name),
                                inval, name,
                                {"label": name,
                                 "name": strutils.to_name(name)})
            acc[uid] = a


def mcountry_transformer(sphere, index, row, acc, field, fields):
    fname = field["name"]
    val = by_path(row, fname, field.get("json"))

    if not val:
        return

    for item in val:
        name = item["country"]
        uid = uniq_id([strutils.to_name(name)])
        if uid not in acc:
            inval = strutils.to_name(name)
            a = utils.to_action(index, "dict", strutils.to_name(name),
                                inval, name,
                                {"label": name,
                                 "name": strutils.to_name(name)})
            acc[uid] = a

HOTELS_CFG = [
    {"name": "_id", "transformer": object_rating},
    {"name": "name", "transformer": name_transformer},
    {"name": "stars",
     "json": ["data"],
     "object_mapping": {"type": "integer", "store": True},
     "convert": float_floor_conv},
    {"name": "range",
     "filter_name": "price_range",
     "json": ["data", "price"],
     "object_mapping": {"type": "integer", "store": True},
     "convert": int_conv},
    {"name": "location",
     "json": ["data"],
     "transformer": location_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"}},
    {"name": "country",
     "json": ["data", "location_tree"],
     "catalog": True,
     "transformer": country_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "is_attribute": True,
     "label": {"en": "Countries"}},
    {"name": "admin1",
     "json": ["data", "location_tree"],
     "catalog": True,
     "transformer": admin1_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "is_attribute": True,
     "label": {"en": "Regions"}},
    {"name": "city",
     "json": ["data", "location_tree"],
     "catalog": True,
     "transformer": city_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "is_attribute": True,
     "label": {"en": "Cities"}},
    {"name": "amenities",
     "json": ["data"],
     "transformer": list_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "convert": list_conv,
     "is_attribute": True,
     "label": {"en": "Amenities"}},
    {"name": "criteria"}
]

MOVIES_CFG = [
    {"name": "_id", "transformer": object_rating},
    {"name": "name", "transformer": name_transformer},
    {"name": "year",
     "json": ["data"],
     "filter_name": "years",
     "object_mapping": {"type": "integer", "store": True},
     "convert": int_conv},
    {"name": "genres",
     "json": ["data", "info"],
     "transformer": list_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "convert": list_conv,
     "is_attribute": True,
     "label": {"en": "Genres"}},
    {"name": "countries",
     "json": ["data", "info"],
     "transformer": mcountry_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "convert": country_conv,
     "is_attribute": True,
     "label": {"en": "Countries"}},
    {"name": "director",
     "filter_name": "directors",
     "json": ["data", "cast_info"],
     "transformer": people_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "convert": director_list_conv,
     "is_attribute": True,
     "label": {"en": "Directors"}},
    {"name": "actor",
     "filter_name": "actors",
     "json": ["data", "cast_info"],
     "transformer": people_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "convert": director_list_conv,
     "is_attribute": True,
     "label": {"en": "Actors"}},
    {"name": "producer",
     "filter_name": "producers",
     "json": ["data", "cast_info"],
     "transformer": people_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "convert": director_list_conv,
     "is_attribute": True,
     "label": {"en": "Producers"}},
    {"name": "writer",
     "filter_name": "writers",
     "json": ["data", "cast_info"],
     "transformer": people_transformer,
     "object_mapping": {"type": "string", "index": "not_analyzed"},
     "convert": director_list_conv,
     "is_attribute": True,
     "label": {"en": "Writers"}},
    {"name": "criteria"}
]

DEFAULT_CFG = [
    {"name": "_id", "transformer": object_rating},
    {"name": "name", "transformer": name_transformer},
    {"name": "criteria"}
]

INDICES = {"hotels": HOTELS_CFG, "movies": MOVIES_CFG}

DEFAULT_CRITERION = {"hotels": "general-hotel-quality", "movies": "movies"}

# Object data extractors for spheres
EXTRACTORS = {"hotels": HotelsExtractor,
              "restaurants": RestaurantsExtractor,
              "movies": MoviesExtractor}

SPHERES_CONFIG = {
    hotels.NAME: hotels.CONFIG}
