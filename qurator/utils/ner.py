import pandas as pd
import requests
import unicodedata
import json


def ner(tsv, ner_rest_endpoint):

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
    for idx, row in tsv.iterrows():

        row_token = unicodedata.normalize('NFC', str(row.TOKEN).replace(' ', ''))

        ner_token_concat = ''
        while row_token != ner_token_concat:

            ner_token, ner_tag, sentence_break, sen = next(result_sequence)
            ner_token_concat += ner_token

            try:
                assert len(row_token) >= len(ner_token_concat)

                if sentence_break:
                    word_num = 0
                else:
                    tsv_result.append((word_num, ner_token, ner_tag, 'O', '-', row.url_id, row.left, row.right, row.top,
                                       row.bottom))
                    word_num += 1
            except AssertionError as e:
                print("ner tokens do not match original at line: {}, ner token: {}. Sentence: {}".
                        format(idx, ner_token, sen))
                raise e

    return pd.DataFrame(tsv_result, columns=['No.', 'TOKEN', 'NE-TAG', 'NE-EMB', 'ID', 'url_id',
                                             'left', 'right', 'top', 'bottom']), ner_result
