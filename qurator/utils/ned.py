import os
import requests
import json


def parse_sentence(sent, normalization_map=None):
    entities = []
    entity_types = []
    entity = []
    ent_type = None

    for p in sent:

        if len(entity) > 0 and (p['prediction'] == 'O' or p['prediction'].startswith('B-')
                                or p['prediction'][2:] != ent_type):
            entities += len(entity) * [" ".join(entity)]
            entity_types += len(entity) * [ent_type]
            entity = []
            ent_type = None

        if p['prediction'] != 'O':
            entity.append(p['word'])

            if ent_type is None:
                ent_type = p['prediction'][2:]
        else:
            entities.append("")
            entity_types.append("")

    if len(entity) > 0:
        entities += len(entity) * [" ".join(entity)]
        entity_types += len(entity) * [ent_type]

    entity_ids = ["{}-{}".format(entity, ent_type) for entity, ent_type in zip(entities, entity_types)]

    if normalization_map is not None:
        text_json = json.dumps(
            ["".join([normalization_map[c] if c in normalization_map else c for c in p['word']]) for p in sent])

        tags_json = json.dumps([p['prediction'] for p in sent])

        entities_json = json.dumps(entity_ids)

        return entity_ids, entities, entity_types, text_json, tags_json, entities_json
    else:
        return entity_ids, entities, entity_types


def count_entities(ner, counter, min_len=4):

    type_agnostic = False if len(counter) == 3 and type(counter[counter.keys()[0]]) == dict else True

    for sent in ner:

        entity_ids, entities, entity_types = parse_sentence(sent)

        already_processed = set()

        for entity_id, entity, ent_type in zip(entity_ids, entities, entity_types):

            if len(entity) < min_len:
                continue

            if entity_id in already_processed:
                continue

            already_processed.add(entity_id)

            if type_agnostic:
                if entity_id in counter:
                    counter[entity_id] += 1
                else:
                    counter[entity_id] = 1
            else:
                if entity in counter[ent_type]:
                    counter[ent_type][entity] += 1
                else:
                    counter[ent_type][entity] = 1


def ned(tsv, ner_result, ned_rest_endpoint, json_file=None, threshold=None, priority=None, max_candidates=None,
        max_dist=None, not_after=None, ned_result=None):

    return_full = json_file is not None

    if ned_result is not None:
        pass

    elif json_file is not None and os.path.exists(json_file):

        print('Loading {}'.format(json_file))

        with open(json_file, "r") as fp:
            ned_result = json.load(fp)

    else:

        resp = requests.post(url=ned_rest_endpoint + '/parse', json=ner_result)

        resp.raise_for_status()

        ner_parsed = json.loads(resp.content)

        ned_rest_endpoint = ned_rest_endpoint + '/ned?return_full=' + str(int(return_full)).lower()

        if priority is not None:
            ned_rest_endpoint += "&priority=" + str(int(priority))

        if return_full:
            ned_rest_endpoint += "&threshold=0.01"  # The JSON representation of the full results permits evaluation
            # for an arbitrary threshold >= 0.01

        elif threshold is not None:
            ned_rest_endpoint += "&threshold=" + str(float(threshold))

        if max_candidates is not None:
            ned_rest_endpoint += "&max_candidates=" + str(int(max_candidates))

        if max_dist is not None:
            ned_rest_endpoint += "&max_dist=" + str(float(max_dist))

        if not_after is not None:
            ner_parsed['__CONTEXT__'] = \
                {
                    'time': {
                        'not_after': not_after
                    }
                }

        resp = requests.post(url=ned_rest_endpoint, json=ner_parsed, timeout=3600000)

        resp.raise_for_status()

        ned_result = json.loads(resp.content)

    rids = []
    entity = ""
    entity_type = None
    tsv['ID'] = '-'
    tsv['conf'] = '-'

    def check_entity(tag):
        nonlocal entity, entity_type, rids

        if (entity != "") and ((tag == 'O') or tag.startswith('B-') or (tag[2:] != entity_type)):

            eid = entity + "-" + entity_type

            if eid in ned_result:
                if 'ranking' in ned_result[eid]:
                    ranking = ned_result[eid]['ranking']

                    tmp = "|".join([ranking[i][1]['wikidata']
                                    for i in range(len(ranking))
                                    if threshold is None or ranking[i][1]['proba_1'] >= threshold])
                    tsv.loc[rids, 'ID'] = tmp if len(tmp) > 0 else '-'

                    tmp = ",".join([str(ranking[i][1]['proba_1'])
                                    for i in range(len(ranking))
                                    if threshold is None or ranking[i][1]['proba_1'] >= threshold])

                    tsv.loc[rids, 'conf'] = tmp if len(tmp) > 0 else '-'
                else:
                    tsv.loc[rids, 'ID'] = 'NIL'
                    tsv.loc[rids, 'conf'] = '-'
            else:
                tsv.loc[rids, 'ID'] = 'NIL'
                tsv.loc[rids, 'conf'] = '-'

            rids = []
            entity = ""
            entity_type = None

    ner_tmp = tsv.copy()
    ner_tmp.loc[~ner_tmp['NE-TAG'].isin(['O', 'B-PER', 'B-LOC', 'B-ORG', 'I-PER', 'I-LOC', 'I-ORG']), 'NE-TAG'] = 'O'

    for rid, row in ner_tmp.iterrows():

        check_entity(row['NE-TAG'])

        if row['NE-TAG'] != 'O':

            entity_type = row['NE-TAG'][2:]

            entity += " " if entity != "" else ""

            entity += str(row['TOKEN'])

            rids.append(rid)

    check_entity('O')

    return tsv, ned_result
