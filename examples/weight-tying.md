# STE render: weight tying in GPT-2

## Original

GPT-2 ties the token embedding matrix `wte` (shape `[50257, 768]` in the 124M model) to the
output projection `lm_head`, so the same parameters both map token ids into the residual
stream and map the final hidden state back to logits; this removes roughly 38.6M parameters
— about 31% of the 124M total — and acts as a regularizer, since gradients from the output
softmax now also update input representations, although it implicitly assumes that a token's
"meaning as input" and "likelihood as output" can live in one space, which is not guaranteed
and is why some later models untie them unless parameter budget dominates.

## STE view

GPT-2 uses one matrix for two jobs. The matrix is `wte`, with shape `[50257, 768]` in the
124M model.

The first job is input. `wte` changes each token id into a vector for the residual stream.

The second job is output. The output projection `lm_head` uses the same parameters. It
changes the final hidden state back into logits.

This sharing removes approximately 38.6M parameters. That is about 31% of the 124M total.

Sharing also acts as a regularizer. Gradients from the output softmax now also update the
input vectors.

The method has an assumption. It assumes that one space can hold the meaning of a token as
input and its likelihood as output. This is not guaranteed. For this reason, some later models
do not share the matrix, unless the parameter budget is the main limit.

## Preserved terms

- `wte`
- `lm_head`
- `[50257, 768]`
- 124M
- 38.6M

## Claims

```json
[
  {"id": "C1", "claim": "wte is shared with lm_head", "anchors": ["wte", "lm_head"]},
  {"id": "C2", "claim": "wte shape is [50257, 768] in the 124M model", "anchors": ["[50257, 768]", "124M"]},
  {"id": "C3", "claim": "tying removes ~38.6M params, ~31% of total", "anchors": ["38.6M", "31%"]},
  {"id": "C4", "claim": "tying acts as a regularizer via output-softmax gradients", "anchors": ["regularizer", "softmax"]},
  {"id": "C5", "claim": "the shared-space assumption is not guaranteed", "anchors": ["not guaranteed"]},
  {"id": "C6", "claim": "some later models untie unless parameter budget dominates", "anchors": ["unless", "parameter budget"]}
]
```
