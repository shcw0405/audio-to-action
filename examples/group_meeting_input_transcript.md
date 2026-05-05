# Example — group meeting input transcript

This is a synthesized example of what the **cleaned transcript** looks like
after `prompts/clean_transcript.md` has been applied to the raw ASR output
of a typical weekly group meeting. It is the input to the
`group_meeting` preset.

> Source: `examples/2026-05-04-group-meeting.mp3` (38m 12s, 3 speakers,
> diarization on)
> Speakers in this file have **not** been mapped to real names yet — that
> is what `SPEAKER_01 / 02 / 03` exists for.

---

**[SPEAKER_01 | 00:08]** 大家好，我们开始本周的组会。先按惯例，每个人讲一下进展。先从张同学开始吧。

**[SPEAKER_02 | 00:21]** 好的。这周我主要做了 baseline 的复现，目前在 CIFAR-10 上的精度大概是 92.3，比 paper 报的低 0.5 个点。我对比了一下学习率 schedule，怀疑是 warmup step 数没对齐。

**[SPEAKER_01 | 00:48]** 嗯。这个差距可以接受。下周三之前你能把 ImageNet 上的 baseline 跑通吗？只要先有一个数能对上就行，code 也整理一下，到时候发我一份。

**[SPEAKER_02 | 01:05]** 可以，下周三前应该没问题。

**[SPEAKER_01 | 01:10]** 好。李同学呢？

**[SPEAKER_03 | 01:14]** 我这边在看 attention 那部分。我把 LayerNorm 的位置换了一下做消融，发现 pre-norm 比 post-norm 在我们这个 setting 下稳定一些。还有一个观察是，head 数从 8 加到 16，验证集 loss 反而上升了，我还在看是不是 batch size 没调。

**[SPEAKER_01 | 01:48]** 这个 head 数的事情挺重要，你专门跑一组消融出来。维度从 8、12、16、24 都跑一下，每组三个 seed，下周组会讲。同时把 batch size 固定，别让两个变量一起动。

**[SPEAKER_03 | 02:12]** 行，我下周组会讲。

**[SPEAKER_01 | 02:18]** 然后还有数据这块。之前说的清洗工作，谁负责来着？

**[SPEAKER_02 | 02:24]** 我之前在做，但后来切去做 baseline 了。

**[SPEAKER_01 | 02:31]** 那这块就先放一下吧，等 baseline 稳住再回来做。如果有时间可以试试自动去重的脚本，但不是这周的任务。

**[SPEAKER_03 | 02:48]** 老师，我有一个问题，关于评测集划分。我们是要严格按 paper 的划分，还是按我们自己的？

**[SPEAKER_01 | 02:58]** 按 paper 的，这样可比。如果有不同我们最后再讨论。

**[SPEAKER_01 | 03:08]** 那今天就到这。下周三前张同学发我 ImageNet baseline，李同学下周组会讲 head 数消融。其他事情按部就班。
