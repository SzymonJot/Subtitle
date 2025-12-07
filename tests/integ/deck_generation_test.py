import json,ast
from common.schemas import BuildDeckRequest
from nlp.lexicon.schema import AnalyzedEpisode
from deck.deck_generation import select_candidates, choose_example, translate_selection

srt_path = "tests/integ/data_preview.txt"

with open(srt_path, "r", encoding="utf-8") as f:
    srt_content = f.read()

raw_json_str = ast.literal_eval(srt_content)   
loaded_analysis = json.loads(raw_json_str)

###############################################
from tests.integ.example_request import request
##############################################3

episode_data = AnalyzedEpisode(**loaded_analysis)
build_request = BuildDeckRequest(**request)

selected = select_candidates(episode_data,build_request)
print(selected)


print("Test completed")
#
#print(len(set(episode_data.episode_data_processed)))
#cands = select_candidates(episode_data,build_request)
#s = choose_example(cands, episode_data, build_request)
#print(s)
#translate_selection(s,'t','t')
    #print(len(cands))
#
    #print(sum([x['cov_share'] for x in cands]))
   #
    #
    #print(len(cands))
    #cands = score_and_rank(cands,req,1)
    #contr = apply_constraints(cands,req)
    #print(sum(c['cov_share'] for c in cands))
    #print("Pool size:", len(contr))
    #
    #print("Sum cov_share:", sum(c['cov_share'] for c in contr))
    ##print(cands)
    #
    #picked, rep = pick_until_target(
    #filtered_ranked=contr,                      # List[RankedCandidate] (dicts)
    #max_cards=req.max_cards,
    #target_coverage=req.target_coverage,
    #max_share_per_pos=req.max_share_per_pos,    # e.g., {"NOUN": 0.5, "VERB": 0.5}
    #target_share_per_pos=req.target_share_per_pos,  # optional, e.g., {"NOUN": 0.5, "VERB": 0.5}
    #)


    #assert all(x['pos'] == 'NOUN' or x['pos'] == 'VERB' for x in cands)


    