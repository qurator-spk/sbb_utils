import pandas as pd
import requests
import unicodedata
import json


def ner(tsv, ner_rest_endpoint, keep_tokenization=False):

    resp = requests.post(url=ner_rest_endpoint, json={'text': " ".join(tsv.TOKEN.astype(str).tolist())})

    resp.raise_for_status()

    def iterate_ner_results(result_sentences):

        for sen in result_sentences:

            for token in sen:

                yield unicodedata.normalize('NFC', token['word']), token['prediction'], False, sen

            yield '', '', True, sen

    ner_result = json.loads(resp.content)

    result_sequence = iterate_ner_results(ner_result)

    tsv_result = []
    word_num = 0

    prev_row_token_tag = 'O'
    prev_ner_token_tag = 'O'

    for idx, row in tsv.iterrows():

        row_token = unicodedata.normalize('NFC', str(row.TOKEN).replace(' ', ''))
        row_token_tag_prefixes = set()
        row_token_tag_types = set()
        row_token_has_sentence_break = False

        ner_token_concat = ''

        while row_token != ner_token_concat:

            ner_token, ner_tag, sentence_break, cur_sen = next(result_sequence)

            ner_token_concat += ner_token

            if prev_ner_token_tag == 'O' and ner_tag.startswith('I'):
                ner_tag = 'B' + ner_tag[1:]

            if len(ner_tag) >= 5 and len(prev_ner_token_tag) >= 5 and ner_tag[2:] != prev_ner_token_tag[2:]:
                ner_tag = 'B' + ner_tag[1:]

            if not sentence_break and len(ner_tag) >= 5:
                row_token_tag_types.add(ner_tag[2:])
                row_token_tag_prefixes.add(ner_tag[0])

            row_token_has_sentence_break |= sentence_break

            try:
                assert len(row_token) >= len(ner_token_concat)

                if not keep_tokenization:
                    if sentence_break:
                        word_num = 0
                        prev_ner_token_tag = 'O'
                    else:
                        tsv_result.append((word_num, ner_token, ner_tag, 'O', '-', row.url_id, row.left, row.right, row.top,
                                           row.bottom))
                        word_num += 1
                        prev_ner_token_tag = ner_tag
                else:
                    prev_ner_token_tag = ner_tag

            except AssertionError as e:
                # import ipdb;ipdb.set_trace()
                print("NER tokens do not match original at line: {}, ner token: {}. Sentence: {}".
                        format(idx, ner_token, cur_sen))
                raise e

        try:
            assert row_token == ner_token_concat
        except AssertionError as e:
            # import ipdb;ipdb.set_trace()
            print("Concatenated NER tokens do not add up to original row token. Row token: {} Concatenated tokens: {}".
                  format(row_token, ner_token_concat))
            raise e

        if keep_tokenization:

            row_token_tag_types = list(row_token_tag_types)

            if len(row_token_tag_types) > 1:
                print("Multiple NER tag types ({})have been assigned to single TSV-token: {}".
                      format(row_token_tag_types, row_token))

            if row_token_has_sentence_break:
                word_num = 0
                prev_row_token_tag = 'O'

            if len(row_token_tag_types) == 0:
                row_token_tag = 'O'
            elif prev_row_token_tag == 'O' or 'B' in row_token_tag_prefixes \
                    or prev_row_token_tag[-3:] not in row_token_tag_types:
                row_token_tag = "B-" + row_token_tag_types[0]
            else:
                row_token_tag = "I-" + row_token_tag_types[0]

            tsv_result.append((word_num, row.TOKEN, row_token_tag, 'O', '-',
                              row.url_id, row.left, row.right, row.top, row.bottom))
            word_num += 1

            prev_row_token_tag = row_token_tag

    return pd.DataFrame(tsv_result, columns=['No.', 'TOKEN', 'NE-TAG', 'NE-EMB', 'ID', 'url_id',
                                             'left', 'right', 'top', 'bottom']), ner_result
