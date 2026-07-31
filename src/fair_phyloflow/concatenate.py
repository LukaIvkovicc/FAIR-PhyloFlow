from __future__ import annotations

from pathlib import Path

from Bio import SeqIO


def discover_alignment_files(alignments_dir: Path) -> list[Path]:
    return sorted(list(alignments_dir.glob("*.fa")) + list(alignments_dir.glob("*.fasta")))


def concatenate_alignments(alignments_dir: Path, out_fasta: Path, *, loci_paths: list[Path] | None = None) -> Path:
    loci = sorted(loci_paths) if loci_paths is not None else discover_alignment_files(alignments_dir)
    if not loci:
        raise ValueError(f"No alignment files selected for concatenation: {alignments_dir}")
    taxon_to_locus_seq: dict[str, dict[Path, str]] = {}
    locus_lengths: dict[Path, int] = {}

    for locus_path in loci:
        records = list(SeqIO.parse(str(locus_path), "fasta"))
        if not records:
            continue
        lengths = {len(str(r.seq)) for r in records}
        if len(lengths) != 1:
            raise ValueError(f"Alignment has unequal sequence lengths: {locus_path}")
        seen: set[str] = set()
        for r in records:
            taxon = r.id
            if taxon in seen:
                raise ValueError(f"Alignment has duplicate taxon ID '{taxon}': {locus_path}")
            seen.add(taxon)
            taxon_to_locus_seq.setdefault(taxon, {})[locus_path] = str(r.seq)
        locus_lengths[locus_path] = lengths.pop()

    if not locus_lengths:
        raise ValueError(f"No parseable alignment records found: {alignments_dir}")

    out_fasta.parent.mkdir(parents=True, exist_ok=True)
    with out_fasta.open("w", encoding="utf-8") as f:
        for taxon in sorted(taxon_to_locus_seq.keys()):
            parts = [
                taxon_to_locus_seq[taxon].get(locus_path, "-" * locus_lengths[locus_path])
                for locus_path in loci
                if locus_path in locus_lengths
            ]
            f.write(f">{taxon}\n{''.join(parts)}\n")
    return out_fasta
