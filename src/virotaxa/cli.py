"""Command-line interface for virotaxa.

Provides commands for downloading, caching, and cataloging viral taxa
from the Virus-Host Database.
"""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="virotaxa",
    help="Reproducible viral taxa selection from Virus-Host Database",
    no_args_is_help=True,
)
console = Console()

# Sub-applications
cache_app = typer.Typer(help="Manage VHDB version cache")
catalog_app = typer.Typer(help="Build and validate catalogs")
genome_app = typer.Typer(help="Fetch and manage genome sequences")

app.add_typer(cache_app, name="cache")
app.add_typer(catalog_app, name="catalog")
app.add_typer(genome_app, name="genome")


# =============================================================================
# Top-level commands
# =============================================================================


@app.command("download")
def download(
    output: Path = typer.Option(
        Path("data/vhdb.tsv"),
        "-o", "--output",
        help="Output file path",
    ),
) -> None:
    """Download the latest Virus-Host Database.

    Downloads the VHDB TSV file with metadata for reproducibility tracking.
    """
    from virotaxa.vhdb.download import download_vhdb

    console.print("[blue]Downloading Virus-Host Database...[/blue]")
    path = download_vhdb(output)
    console.print(f"[green]Downloaded to {path}[/green]")

    metadata_path = path.with_suffix(".metadata.json")
    if metadata_path.exists():
        console.print(f"[dim]Metadata saved to {metadata_path}[/dim]")


@app.command("info")
def info(
    vhdb_file: Path = typer.Argument(..., help="Path to VHDB TSV file"),
) -> None:
    """Show statistics for a Virus-Host Database file."""
    from virotaxa.vhdb.download import get_vhdb_metadata
    from virotaxa.vhdb.parse import load_vhdb

    if not vhdb_file.exists():
        console.print(f"[red]File not found: {vhdb_file}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]VHDB Info: {vhdb_file}[/bold blue]")
    console.print("=" * 50)

    # Load and show statistics
    df = load_vhdb(vhdb_file)
    console.print(f"\nTotal relationships: {len(df):,}")
    console.print(f"Unique viruses: {df['virus_tax_id'].nunique():,}")
    console.print(f"Unique hosts: {df['host_tax_id'].nunique():,}")

    # Evidence distribution
    console.print("\n[bold]Evidence types:[/bold]")
    for evidence, count in df["evidence"].value_counts().items():
        console.print(f"  {evidence}: {count:,}")

    # Show metadata if available
    metadata = get_vhdb_metadata(vhdb_file)
    if metadata:
        console.print("\n[bold]Download metadata:[/bold]")
        console.print(f"  Downloaded: {metadata.get('download_timestamp', 'unknown')}")
        console.print(f"  SHA256: {metadata.get('sha256', 'unknown')[:16]}...")


@app.command("families")
def families(
    vhdb_file: Path = typer.Argument(..., help="Path to VHDB TSV file"),
    mode: str = typer.Option(
        "clinical",
        "-m", "--mode",
        help="Filter mode: clinical, pandemic, or mammal",
    ),
) -> None:
    """List viral families in the database."""
    from virotaxa.vhdb.filters import filter_by_host
    from virotaxa.vhdb.parse import load_vhdb
    from virotaxa.vhdb.taxonomy import extract_taxonomy

    if not vhdb_file.exists():
        console.print(f"[red]File not found: {vhdb_file}[/red]")
        raise typer.Exit(1)

    df = load_vhdb(vhdb_file)
    filtered = filter_by_host(df, mode=mode)

    # Extract families
    families_list: list[str] = []
    for lineage in filtered["virus_lineage"].dropna():
        taxonomy = extract_taxonomy(lineage)
        if taxonomy["family"]:
            families_list.append(taxonomy["family"])

    family_counts = {}
    for f in families_list:
        family_counts[f] = family_counts.get(f, 0) + 1

    console.print(f"[bold blue]Viral Families ({mode} mode)[/bold blue]")
    console.print("=" * 50)
    console.print(f"\nTotal families: {len(family_counts)}\n")

    # Sort by count
    for family, count in sorted(family_counts.items(), key=lambda x: -x[1])[:30]:
        console.print(f"  {family}: {count:,}")

    if len(family_counts) > 30:
        console.print(f"\n  ... and {len(family_counts) - 30} more")


# =============================================================================
# Cache commands
# =============================================================================


@cache_app.command("download")
def cache_download_cmd() -> None:
    """Download latest VHDB directly to cache.

    Downloads and caches the latest VHDB for future reproducible use.
    """
    from virotaxa.cache import cache_download

    console.print("[blue]Downloading VHDB to cache...[/blue]")

    try:
        cached_path, file_hash = cache_download()
        console.print("[green]Downloaded and cached successfully[/green]")
        console.print(f"  Hash: {file_hash[:12]}")
        console.print(f"  Path: {cached_path}")
        console.print(f"\n[dim]To use this version:[/dim]")
        console.print(f"  virotaxa cache use {file_hash[:12]} -o data/vhdb.tsv")
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise typer.Exit(1)


@cache_app.command("list")
def cache_list_cmd() -> None:
    """List all cached VHDB versions."""
    from virotaxa.cache import list_cached

    versions = list_cached()

    console.print("[bold blue]Cached VHDB Versions[/bold blue]")
    console.print("=" * 60)

    if not versions:
        console.print("\n[yellow]No cached versions found.[/yellow]")
        console.print("Run 'virotaxa cache download' to cache a version.")
        return

    console.print(f"\n{'Hash':<14} {'Downloaded':<22} {'Size':<12} {'Cached At'}")
    console.print("-" * 60)

    for v in versions:
        size_mb = v["file_size_bytes"] / 1024 / 1024
        download_ts = v.get("download_timestamp") or "unknown"
        console.print(
            f"{v['short_hash']:<14} "
            f"{download_ts[:19] if download_ts != 'unknown' else download_ts:<22} "
            f"{size_mb:>6.1f} MB    "
            f"{v['cached_at'][:10]}"
        )

    console.print(f"\nTotal: {len(versions)} cached version(s)")


@cache_app.command("use")
def cache_use_cmd(
    hash_prefix: str = typer.Argument(..., help="Hash prefix (at least 8 chars)"),
    output: Path = typer.Option(
        Path("data/vhdb.tsv"),
        "-o", "--output",
        help="Output path",
    ),
    copy: bool = typer.Option(
        False,
        "--copy/--link",
        help="Copy file instead of symlink",
    ),
) -> None:
    """Use a cached VHDB version.

    Retrieves a cached VHDB by hash prefix and copies/links to output path.
    """
    import shutil

    from virotaxa.cache import get_cached

    if len(hash_prefix) < 8:
        console.print("[red]Hash prefix must be at least 8 characters[/red]")
        raise typer.Exit(1)

    try:
        cached_path = get_cached(hash_prefix)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if cached_path is None:
        console.print(f"[red]No cached version found for: {hash_prefix}[/red]")
        console.print("Run 'virotaxa cache list' to see available versions.")
        raise typer.Exit(1)

    # Ensure output directory exists
    output.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing if exists
    if output.exists() or output.is_symlink():
        output.unlink()

    if copy:
        shutil.copy2(cached_path, output)
        console.print(f"[green]Copied cached version to {output}[/green]")
    else:
        output.symlink_to(cached_path.resolve())
        console.print(f"[green]Linked cached version to {output}[/green]")

    console.print(f"[dim]Source: {cached_path}[/dim]")


@cache_app.command("add")
def cache_add_cmd(
    vhdb_file: Path = typer.Argument(..., help="Path to VHDB TSV file"),
) -> None:
    """Add a VHDB file to the cache."""
    from virotaxa.cache import add_to_cache

    if not vhdb_file.exists():
        console.print(f"[red]File not found: {vhdb_file}[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Adding {vhdb_file} to cache...[/blue]")
    file_hash = add_to_cache(vhdb_file)
    console.print(f"[green]Cached with hash: {file_hash[:12]}[/green]")
    console.print(f"[dim]Full hash: {file_hash}[/dim]")


@cache_app.command("remove")
def cache_remove_cmd(
    hash_prefix: str = typer.Argument(..., help="Hash prefix (at least 8 chars)"),
    force: bool = typer.Option(False, "-f", "--force", help="Skip confirmation"),
) -> None:
    """Remove a cached VHDB version."""
    from virotaxa.cache import get_cached, remove_cached

    if len(hash_prefix) < 8:
        console.print("[red]Hash prefix must be at least 8 characters[/red]")
        raise typer.Exit(1)

    try:
        cached_path = get_cached(hash_prefix)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if cached_path is None:
        console.print(f"[red]No cached version found: {hash_prefix}[/red]")
        raise typer.Exit(1)

    if not force:
        console.print(f"About to remove: {cached_path.name}")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    try:
        if remove_cached(hash_prefix):
            console.print(f"[green]Removed: {hash_prefix}[/green]")
        else:
            console.print(f"[red]Failed to remove: {hash_prefix}[/red]")
            raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Catalog commands
# =============================================================================


@catalog_app.command("build")
def catalog_build_cmd(
    vhdb_file: Path = typer.Argument(..., help="Path to VHDB TSV file"),
    output: Path = typer.Option(
        Path("catalog.tsv"),
        "-o", "--output",
        help="Output catalog file",
    ),
    mode: str = typer.Option(
        "clinical",
        "-m", "--mode",
        help="Catalog mode: clinical, pandemic, or mammal",
    ),
    exclude_bacteriophages: bool = typer.Option(
        True,
        "--exclude-bacteriophages/--include-bacteriophages",
        help="Exclude bacteriophage families",
    ),
) -> None:
    """Build a viral taxa catalog from VHDB.

    \b
    Modes:
      clinical  - Human hosts only (~1,400 viruses)
      pandemic  - All vertebrate hosts (~4,000+ viruses)
      mammal    - Mammalian hosts only
    """
    from virotaxa.catalog.builder import build_catalog, save_catalog

    if not vhdb_file.exists():
        console.print(f"[red]File not found: {vhdb_file}[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Building {mode} catalog...[/blue]")

    catalog = build_catalog(
        vhdb_file,
        mode=mode,
        exclude_bacteriophages=exclude_bacteriophages,
    )

    tsv_path, meta_path = save_catalog(
        catalog=catalog,
        output_path=output,
        vhdb_path=vhdb_file,
        mode=mode,
        exclude_bacteriophages=exclude_bacteriophages,
    )

    console.print(f"[green]Built catalog with {len(catalog)} taxa[/green]")
    console.print(f"  Families: {catalog['family'].nunique()}")
    console.print(f"  RefSeq entries: {catalog['refseq_ids'].apply(len).sum()}")
    console.print(f"\n  Catalog: {tsv_path}")
    console.print(f"  Metadata: {meta_path}")


@catalog_app.command("validate")
def catalog_validate_cmd(
    catalog_file: Path = typer.Argument(..., help="Path to catalog TSV file"),
) -> None:
    """Validate a catalog against its metadata.

    Checks catalog integrity and reproducibility.
    """
    from virotaxa.catalog.validate import validate_catalog

    if not catalog_file.exists():
        console.print(f"[red]Catalog not found: {catalog_file}[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Catalog Validation[/bold blue]")
    console.print("=" * 50)

    result = validate_catalog(catalog_file)

    # Show info
    for key, value in result.info.items():
        console.print(f"[green]\u2713[/green] {key}: {value}")

    # Show warnings
    for warning in result.warnings:
        console.print(f"[yellow]\u26a0 {warning}[/yellow]")

    # Show errors
    for error in result.errors:
        console.print(f"[red]\u2717 {error}[/red]")

    # Summary
    console.print()
    if result.is_valid:
        if result.warnings:
            console.print(
                f"[yellow]Validation PASSED with {len(result.warnings)} warning(s)[/yellow]"
            )
        else:
            console.print("[green]Validation PASSED - catalog is fully reproducible[/green]")
    else:
        console.print(f"[red]Validation FAILED with {len(result.errors)} error(s)[/red]")
        raise typer.Exit(1)


# =============================================================================
# Genome commands
# =============================================================================


@genome_app.command("fetch")
def genome_fetch_cmd(
    catalog: Path = typer.Argument(..., help="Path to catalog TSV file"),
    output: Path = typer.Option(
        Path("genomes"),
        "-o", "--output",
        help="Output directory for FASTA files",
    ),
    email: str = typer.Option(
        ...,
        "--email",
        help="Email for NCBI (required by NCBI policy)",
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="NCBI API key (optional, increases rate limit)",
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        help="Number of sequences per batch request",
    ),
) -> None:
    """Fetch genome sequences for all taxa in a catalog.

    Downloads RefSeq genome sequences from NCBI for each taxon in the catalog.
    Sequences are saved as FASTA files, one per taxon.

    \b
    Examples:
      virotaxa genome fetch clinical_catalog.tsv --email user@example.com
      virotaxa genome fetch catalog.tsv --email user@example.com --api-key KEY -o genomes/
    """
    from virotaxa.genome.fetch import fetch_genomes
    from virotaxa.genome.metadata import save_genome_metadata

    if not catalog.exists():
        console.print(f"[red]Catalog not found: {catalog}[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Fetching genomes from catalog: {catalog}[/blue]")
    console.print(f"Output directory: {output}")

    if api_key:
        console.print("[dim]Using API key (10 req/s rate limit)[/dim]")
    else:
        console.print("[dim]No API key (3 req/s rate limit)[/dim]")

    try:
        result = fetch_genomes(
            catalog_path=catalog,
            output_dir=output,
            email=email,
            api_key=api_key,
            batch_size=batch_size,
        )

        # Save metadata
        metadata_path = save_genome_metadata(
            result=result,
            catalog_path=catalog,
            email=email,
        )

        # Show results
        console.print()
        console.print("[green]Fetch complete![/green]")
        console.print(f"  Taxa: {result.total_taxa}")
        console.print(f"  Sequences: {result.successful}/{result.total_sequences}")

        if result.failed:
            console.print(f"  [yellow]Failed: {len(result.failed)}[/yellow]")

        console.print(f"  Files: {len(result.files)}")
        console.print(f"\n  Output: {output}")
        console.print(f"  Metadata: {metadata_path}")

    except Exception as e:
        console.print(f"[red]Fetch failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
