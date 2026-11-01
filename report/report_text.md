## setup
This assignment compares three prompt versions for EduAssist AI, an academic question-answering assistant that must return strict JSON. All calls used **{model}** through an OpenAI-compatible chat completions API (v1) at {base_url}, on the free tier, with temperature {temperature}, seed {seed} and a {max_tokens}-token output limit. Costs use the provider's published prices of {price_in} (input) and {price_out} (output) {currency} per million tokens, from {pricing_source}, checked on {pricing_date}. The API key was read from an environment variable. Each version ran on the same five questions (15 requests).

## latency
Latency was measured as wall-clock time around each API call. Tasks 1 and 2 report the five prompt v1 requests; the CSV holds all 15 calls. Mean latency was {lat_mean} s, median {lat_median} s, minimum {lat_min} s, maximum {lat_max} s and sample standard deviation {lat_std} s.

## latency_interpretation
The slowest v1 request was {v1_slowest_q} at {v1_slowest_latency} s. It generated {v1_slowest_out} output tokens, against a v1 average of {v1_out}, and generation time grows with output length. If this equals the {max_tokens}-token limit, the answer was probably cut off, which also means its true cost and latency would be slightly higher. Network delay and server load on a shared free-tier service may also contribute, and a single run cannot separate these effects.

## cost
Cost per request is input tokens divided by 1,000,000 times the input price, plus output tokens divided by 1,000,000 times the output price. For prompt v1 the average cost was {v1_cost} {currency} per request, which projects to {v1_monthly} {currency} per month at 10,000 requests. The projected monthly cost is {v1_monthly}, {v2_monthly} and {v3_monthly} {currency} for v1, v2 and v3.

## cost_optimization
Recommendation: cap and shape the output length. Output tokens are the largest part of each request ({v3_out_share}% of the tokens in v3) and are usually priced higher than input tokens. Asking for a short answer and at most three key points, with a sensible token limit, should cut cost and latency without changing the JSON structure. A 25% reduction in v3 output tokens would save about {v3_saving25} {currency} per month at 10,000 requests. Using a smaller model for simple questions is a further option.

## mlflow
The prompts were registered in the MLflow Prompt Registry as {prompt_name} (versions 1 to 3) with commit messages describing each change. One run per version was logged in the experiment {experiment} with avg_latency_seconds, avg_input_tokens, avg_output_tokens, avg_cost_per_request and valid_json. valid_json is valid responses divided by total responses, checked strictly on the raw output, so a code-fenced response counts as invalid; it was computed for all three versions. Version {best} was promoted with the alias production. Screenshots follow the comparison table.

## justification
Prompt v{best} is promoted to production. On JSON validity it is the only version that meets the requirement: {v3_valid_count} of its responses were valid JSON matching the schema, while v1 and v2 scored {v1_valid} and {v2_valid} because they were never asked for JSON. Downstream code needs to parse the answer without cleaning it. On quality, its answers were accurate and on topic, and the confidence and key_points fields add structure that free text lacks. On quality, I read all five answers: they were accurate and on topic, and the confidence and key_points fields add structure that free text lacks.On latency, v3 averaged {v3_latency} s against {v1_latency} s for v1, a {latency_cut}% reduction. On tokens, v3 uses more input tokens ({v3_in} against {v1_in}) because its instructions are longer, but it generates far fewer output tokens ({v3_out} against {v1_out}, a {out_cut}% reduction). Output tokens dominate the bill in this run, so the average cost per request fell from {v1_cost} to {v3_cost} {currency}, a {cost_cut}% reduction. The longer prompt is a good trade: v{best} wins on validity, latency, output tokens and cost, and loses only on input tokens.

## limitations
Results come from five questions, one run per prompt and one model, so latency differences are indicative only and depend on network and server load. The output limit may truncate long answers, and hidden reasoning tokens of a reasoning model count as output. valid_json measures format, not correctness, so quality was checked by reading the answers. Prices were taken on {pricing_date} and may change.
