using System.Diagnostics;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using Mutagen.Bethesda;
using Mutagen.Bethesda.Environments;
using Mutagen.Bethesda.Plugins;
using Mutagen.Bethesda.Plugins.Cache;
using Mutagen.Bethesda.Plugins.Records;
using Mutagen.Bethesda.Skyrim;

var totalTimer = Stopwatch.StartNew();
var options = Options.Parse(args);
Directory.CreateDirectory(options.OutputDirectory);
using var deadline = new Deadline(options.MaxSeconds);

var stagedData = Path.Combine(options.OutputDirectory, "staged-data");
var stageTimer = Stopwatch.StartNew();
var stage = StagePlugins(options, stagedData);
stageTimer.Stop();
Log($"Staged {stage.LoadOrder.Length} plugins in {stageTimer.Elapsed.TotalSeconds:n1}s");

var envTimer = Stopwatch.StartNew();
using var env = GameEnvironment.Typical.Builder<ISkyrimMod, ISkyrimModGetter>(GameRelease.SkyrimSE)
    .WithTargetDataFolder(stagedData)
    .WithLoadOrder(stage.LoadOrder)
    .Build();
envTimer.Stop();
Log($"Loaded Mutagen environment in {envTimer.Elapsed.TotalSeconds:n1}s");

var recipes = new List<RecipeRow>();
var exportTimer = Stopwatch.StartNew();
foreach (var recipe in env.LoadOrder.PriorityOrder.ConstructibleObject().WinningOverrides())
{
    deadline.ThrowIfExpired();
    var created = Resolve<IConstructibleGetter>(env.LinkCache, recipe.CreatedObject.FormKey);
    var workbench = recipe.WorkbenchKeyword.IsNull
        ? null
        : Resolve<IKeywordGetter>(env.LinkCache, recipe.WorkbenchKeyword.FormKey);

    var row = new RecipeRow(
        RecipeFormId: recipe.FormKey.ToString(),
        RecipeEditorId: recipe.EditorID,
        SourcePlugin: recipe.FormKey.ModKey.FileName.String,
        CreatedFormId: recipe.CreatedObject.FormKey.ToString(),
        CreatedEditorId: created?.EditorID,
        CreatedName: DisplayName(created),
        CreatedType: created?.GetType().Name,
        CreatedValue: NumberProperty(created, "Value"),
        CreatedWeight: NumberProperty(created, "Weight"),
        CreatedCount: recipe.CreatedObjectCount ?? 1,
        WorkbenchFormId: recipe.WorkbenchKeyword.IsNull ? null : recipe.WorkbenchKeyword.FormKey.ToString(),
        WorkbenchEditorId: workbench?.EditorID,
        ConditionCount: recipe.Conditions.Count,
        Ingredients: (recipe.Items ?? []).Select(item =>
        {
            var ingredient = Resolve<IItemGetter>(env.LinkCache, item.Item.Item.FormKey);
            return new IngredientRow(
                FormId: item.Item.Item.FormKey.ToString(),
                EditorId: ingredient?.EditorID,
                Name: DisplayName(ingredient),
                Type: ingredient?.GetType().Name,
                Value: NumberProperty(ingredient, "Value"),
                Weight: NumberProperty(ingredient, "Weight"),
                Count: item.Item.Count);
        }).ToList());

    if (!string.IsNullOrWhiteSpace(options.Contains) && !Contains(row, options.Contains))
    {
        continue;
    }

    recipes.Add(row);
}
exportTimer.Stop();
Log($"Resolved {recipes.Count} matching recipes in {exportTimer.Elapsed.TotalSeconds:n1}s");

var manifest = new Manifest(
    GeneratedAt: DateTimeOffset.UtcNow,
    GtsPath: options.GtsPath,
    ProfilePath: options.ProfilePath,
    StagedDataPath: stagedData,
    ActivePluginCount: stage.LoadOrder.Length,
    RecipeCount: recipes.Count,
    Source: "Mutagen.Bethesda 0.53.1 over staged MO2 profile plugins",
    StageSeconds: stageTimer.Elapsed.TotalSeconds,
    EnvironmentSeconds: envTimer.Elapsed.TotalSeconds,
    ExportSeconds: exportTimer.Elapsed.TotalSeconds,
    TotalSeconds: totalTimer.Elapsed.TotalSeconds);

var jsonOptions = new JsonSerializerOptions { WriteIndented = true };
File.WriteAllText(Path.Combine(options.OutputDirectory, "manifest.json"), JsonSerializer.Serialize(manifest, jsonOptions));
WriteSqlite(options.OutputPath, manifest, recipes);

Console.WriteLine($"Exported {recipes.Count} recipes from {stage.LoadOrder.Length} active plugins to {options.OutputPath} in {totalTimer.Elapsed.TotalSeconds:n1}s");

static TGetter? Resolve<TGetter>(ILinkCache<ISkyrimMod, ISkyrimModGetter> linkCache, FormKey formKey)
    where TGetter : class, IMajorRecordGetter
{
    return linkCache.TryResolve<TGetter>(formKey, out var record) ? record : null;
}

static string? DisplayName(object? record)
{
    if (record is null) return null;
    var value = record.GetType().GetProperty("Name")?.GetValue(record);
    var text = value?.ToString();
    return string.IsNullOrWhiteSpace(text) ? null : text;
}

static double? NumberProperty(object? record, string propertyName)
{
    if (record is null) return null;
    var value = record.GetType().GetProperty(propertyName)?.GetValue(record);
    return value is null ? null : Convert.ToDouble(value);
}

static bool Contains(RecipeRow row, string needle)
{
    return Fields().Any(value => value?.Contains(needle, StringComparison.OrdinalIgnoreCase) == true);

    IEnumerable<string?> Fields()
    {
        yield return row.RecipeFormId;
        yield return row.RecipeEditorId;
        yield return row.SourcePlugin;
        yield return row.CreatedFormId;
        yield return row.CreatedEditorId;
        yield return row.CreatedName;
        yield return row.CreatedType;
        yield return row.WorkbenchFormId;
        yield return row.WorkbenchEditorId;
        foreach (var ingredient in row.Ingredients)
        {
            yield return ingredient.FormId;
            yield return ingredient.EditorId;
            yield return ingredient.Name;
            yield return ingredient.Type;
        }
    }
}

static StageResult StagePlugins(Options options, string stagedData)
{
    var timer = Stopwatch.StartNew();
    if (Directory.Exists(stagedData)) Directory.Delete(stagedData, recursive: true);
    Directory.CreateDirectory(stagedData);

    var dataPath = Path.Combine(options.GtsPath, "Game Root", "Data");
    var modsPath = Path.Combine(options.GtsPath, "mods");
    var modDirs = ReadEnabledModDirectories(options.ProfilePath, modsPath).ToList();
    var active = ReadActivePlugins(options.ProfilePath);
    var loadOrder = ReadLoadOrder(options.ProfilePath)
        .Where(plugin => IsImplicitGamePlugin(plugin) || active.Contains(plugin) || File.Exists(Path.Combine(dataPath, plugin)))
        .ToList();
    var desired = new HashSet<string>(loadOrder, StringComparer.OrdinalIgnoreCase);
    var pluginSources = IndexPluginSources(new[] { dataPath }.Concat(modDirs), desired, options);
    Log($"Indexed {pluginSources.Count} plugin files in {timer.Elapsed.TotalSeconds:n1}s");

    var staged = new List<ModKey>();
    foreach (var plugin in loadOrder)
    {
        options.Deadline.ThrowIfExpired();
        if (!pluginSources.TryGetValue(plugin, out var source))
        {
            Console.Error.WriteLine($"Warning: active plugin not found, skipping: {plugin}");
            continue;
        }

        var target = Path.Combine(stagedData, Path.GetFileName(source));
        LinkOrCopy(source, target);
        staged.Add(ModKey.FromFileName(Path.GetFileName(source)));
    }

    if (staged.Count == 0)
    {
        throw new InvalidOperationException("No active plugins were staged. Check --gts-path and --profile.");
    }

    return new StageResult(staged.ToArray());
}

static Dictionary<string, string> IndexPluginSources(IEnumerable<string> sourceDirs, HashSet<string> desired, Options options)
{
    var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    foreach (var dir in sourceDirs)
    {
        options.Deadline.ThrowIfExpired();
        if (!Directory.Exists(dir)) continue;

        foreach (var file in Directory.EnumerateFiles(dir, "*.*", SearchOption.TopDirectoryOnly))
        {
            var name = Path.GetFileName(file);
            if (!desired.Contains(name)) continue;
            result[name] = file;
        }

        if (result.Count == desired.Count) break;
    }
    return result;
}

static void LinkOrCopy(string source, string target)
{
    if (File.Exists(target)) File.Delete(target);
    File.Copy(source, target, overwrite: true);
}

static IEnumerable<string> ReadEnabledModDirectories(string profilePath, string modsPath)
{
    var modList = Path.Combine(profilePath, "modlist.txt");
    if (!File.Exists(modList)) yield break;

    foreach (var raw in File.ReadLines(modList))
    {
        if (!raw.StartsWith('+')) continue;
        var name = raw[1..];
        if (name.EndsWith("_separator", StringComparison.OrdinalIgnoreCase)) continue;
        var path = Path.Combine(modsPath, name);
        if (Directory.Exists(path)) yield return path;
    }
}

static HashSet<string> ReadActivePlugins(string profilePath)
{
    var pluginsPath = Path.Combine(profilePath, "plugins.txt");
    var active = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    foreach (var raw in File.ReadLines(pluginsPath))
    {
        var line = raw.Trim();
        if (!line.StartsWith('*')) continue;
        active.Add(line[1..]);
    }
    return active;
}

static IEnumerable<string> ReadLoadOrder(string profilePath)
{
    foreach (var raw in File.ReadLines(Path.Combine(profilePath, "loadorder.txt")))
    {
        var line = raw.Trim();
        if (line.Length == 0 || line.StartsWith('#')) continue;
        yield return line;
    }
}

static bool IsImplicitGamePlugin(string plugin)
{
    return plugin.Equals("Skyrim.esm", StringComparison.OrdinalIgnoreCase)
        || plugin.Equals("Update.esm", StringComparison.OrdinalIgnoreCase)
        || plugin.Equals("Dawnguard.esm", StringComparison.OrdinalIgnoreCase)
        || plugin.Equals("HearthFires.esm", StringComparison.OrdinalIgnoreCase)
        || plugin.Equals("Dragonborn.esm", StringComparison.OrdinalIgnoreCase);
}

static void WriteSqlite(string path, Manifest manifest, IEnumerable<RecipeRow> recipes)
{
    Directory.CreateDirectory(Path.GetDirectoryName(path)!);
    using var connection = new SqliteConnection($"Data Source={path}");
    connection.Open();
    Execute(connection, "PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF;");
    Execute(connection, """
        CREATE TABLE IF NOT EXISTS manifest (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        DROP TABLE IF EXISTS ingredients;
        DROP TABLE IF EXISTS recipes;
        CREATE TABLE recipes (
          recipe_id INTEGER PRIMARY KEY,
          recipe_formid TEXT NOT NULL,
          recipe_edid TEXT,
          source_plugin TEXT NOT NULL,
          created_formid TEXT NOT NULL,
          created_edid TEXT,
          created_name TEXT,
          created_type TEXT,
          created_value REAL,
          created_weight REAL,
          created_count INTEGER NOT NULL,
          workbench_formid TEXT,
          workbench_edid TEXT,
          condition_count INTEGER NOT NULL
        );
        CREATE TABLE ingredients (
          ingredient_id INTEGER PRIMARY KEY,
          recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id),
          ingredient_formid TEXT NOT NULL,
          ingredient_edid TEXT,
          ingredient_name TEXT,
          ingredient_type TEXT,
          ingredient_value REAL,
          ingredient_weight REAL,
          count INTEGER NOT NULL
        );
        CREATE INDEX idx_recipes_created_name ON recipes(created_name);
        CREATE INDEX idx_recipes_created_edid ON recipes(created_edid);
        CREATE INDEX idx_recipes_workbench ON recipes(workbench_edid);
        CREATE INDEX idx_ingredients_name ON ingredients(ingredient_name);
        CREATE INDEX idx_ingredients_edid ON ingredients(ingredient_edid);
        """);

    InsertManifest(connection, manifest);
    using var transaction = connection.BeginTransaction();
    using var recipeCommand = connection.CreateCommand();
    recipeCommand.Transaction = transaction;
    recipeCommand.CommandText = """
        INSERT INTO recipes (recipe_formid, recipe_edid, source_plugin, created_formid, created_edid, created_name, created_type, created_value, created_weight, created_count, workbench_formid, workbench_edid, condition_count)
        VALUES ($recipe_formid, $recipe_edid, $source_plugin, $created_formid, $created_edid, $created_name, $created_type, $created_value, $created_weight, $created_count, $workbench_formid, $workbench_edid, $condition_count)
        RETURNING recipe_id;
        """;
    AddParameters(recipeCommand, "$recipe_formid", "$recipe_edid", "$source_plugin", "$created_formid", "$created_edid", "$created_name", "$created_type", "$created_value", "$created_weight", "$created_count", "$workbench_formid", "$workbench_edid", "$condition_count");

    using var ingredientCommand = connection.CreateCommand();
    ingredientCommand.Transaction = transaction;
    ingredientCommand.CommandText = """
        INSERT INTO ingredients (recipe_id, ingredient_formid, ingredient_edid, ingredient_name, ingredient_type, ingredient_value, ingredient_weight, count)
        VALUES ($recipe_id, $ingredient_formid, $ingredient_edid, $ingredient_name, $ingredient_type, $ingredient_value, $ingredient_weight, $count);
        """;
    AddParameters(ingredientCommand, "$recipe_id", "$ingredient_formid", "$ingredient_edid", "$ingredient_name", "$ingredient_type", "$ingredient_value", "$ingredient_weight", "$count");

    foreach (var recipe in recipes)
    {
        Set(recipeCommand, "$recipe_formid", recipe.RecipeFormId);
        Set(recipeCommand, "$recipe_edid", recipe.RecipeEditorId);
        Set(recipeCommand, "$source_plugin", recipe.SourcePlugin);
        Set(recipeCommand, "$created_formid", recipe.CreatedFormId);
        Set(recipeCommand, "$created_edid", recipe.CreatedEditorId);
        Set(recipeCommand, "$created_name", recipe.CreatedName);
        Set(recipeCommand, "$created_type", recipe.CreatedType);
        Set(recipeCommand, "$created_value", recipe.CreatedValue);
        Set(recipeCommand, "$created_weight", recipe.CreatedWeight);
        Set(recipeCommand, "$created_count", recipe.CreatedCount);
        Set(recipeCommand, "$workbench_formid", recipe.WorkbenchFormId);
        Set(recipeCommand, "$workbench_edid", recipe.WorkbenchEditorId);
        Set(recipeCommand, "$condition_count", recipe.ConditionCount);
        var recipeId = (long)recipeCommand.ExecuteScalar()!;

        foreach (var ingredient in recipe.Ingredients)
        {
            Set(ingredientCommand, "$recipe_id", recipeId);
            Set(ingredientCommand, "$ingredient_formid", ingredient.FormId);
            Set(ingredientCommand, "$ingredient_edid", ingredient.EditorId);
            Set(ingredientCommand, "$ingredient_name", ingredient.Name);
            Set(ingredientCommand, "$ingredient_type", ingredient.Type);
            Set(ingredientCommand, "$ingredient_value", ingredient.Value);
            Set(ingredientCommand, "$ingredient_weight", ingredient.Weight);
            Set(ingredientCommand, "$count", ingredient.Count);
            ingredientCommand.ExecuteNonQuery();
        }
    }

    transaction.Commit();
}

static void InsertManifest(SqliteConnection connection, Manifest manifest)
{
    using var command = connection.CreateCommand();
    command.CommandText = "INSERT OR REPLACE INTO manifest (key, value) VALUES ($key, $value);";
    AddParameters(command, "$key", "$value");
    foreach (var pair in new Dictionary<string, string>
    {
        ["recipe.generated_at"] = manifest.GeneratedAt.ToString("O"),
        ["recipe.gts_path"] = manifest.GtsPath,
        ["recipe.profile_path"] = manifest.ProfilePath,
        ["recipe.staged_data_path"] = manifest.StagedDataPath,
        ["recipe.active_plugin_count"] = manifest.ActivePluginCount.ToString(),
        ["recipe.recipe_count"] = manifest.RecipeCount.ToString(),
        ["recipe.source"] = manifest.Source,
        ["recipe.stage_seconds"] = manifest.StageSeconds.ToString("n3"),
        ["recipe.environment_seconds"] = manifest.EnvironmentSeconds.ToString("n3"),
        ["recipe.export_seconds"] = manifest.ExportSeconds.ToString("n3"),
        ["recipe.total_seconds"] = manifest.TotalSeconds.ToString("n3")
    })
    {
        Set(command, "$key", pair.Key);
        Set(command, "$value", pair.Value);
        command.ExecuteNonQuery();
    }
}

static void Execute(SqliteConnection connection, string sql)
{
    using var command = connection.CreateCommand();
    command.CommandText = sql;
    command.ExecuteNonQuery();
}

static void AddParameters(SqliteCommand command, params string[] names)
{
    foreach (var name in names) command.Parameters.Add(name, SqliteType.Text);
}

static void Set(SqliteCommand command, string name, object? value)
{
    command.Parameters[name].Value = value ?? DBNull.Value;
}

static void Log(string message)
{
    Console.Error.WriteLine($"[{DateTimeOffset.Now:HH:mm:ss}] {message}");
}

internal sealed record Deadline(int MaxSeconds) : IDisposable
{
    private readonly Stopwatch _timer = Stopwatch.StartNew();

    public void ThrowIfExpired()
    {
        if (_timer.Elapsed.TotalSeconds > MaxSeconds)
        {
            throw new TimeoutException($"Exporter exceeded --max-seconds {MaxSeconds}.");
        }
    }

    public void Dispose()
    {
        _timer.Stop();
    }
}

internal sealed record Options(string GtsPath, string ProfilePath, string OutputPath, string? Contains, int MaxSeconds)
{
    public Deadline Deadline { get; } = new(MaxSeconds);
    public string OutputDirectory => Path.GetDirectoryName(OutputPath)!;

    public static Options Parse(string[] args)
    {
        var gtsPath = "/mnt/e/games/GTSAV";
        string? profilePath = null;
        var output = Path.Combine("cache", "gts-index", "gts.sqlite");
        string? contains = null;
        var maxSeconds = 120;

        for (var i = 0; i < args.Length; i++)
        {
            var arg = args[i];
            string Next() => i + 1 < args.Length ? args[++i] : throw new ArgumentException($"Missing value for {arg}");
            switch (arg)
            {
                case "--gts-path": gtsPath = Next(); break;
                case "--profile": profilePath = Next(); break;
                case "--out": output = Next(); break;
                case "--contains": contains = Next(); break;
                case "--max-seconds": maxSeconds = int.Parse(Next()); break;
                case "--help": PrintHelpAndExit(); break;
                default: throw new ArgumentException($"Unknown argument: {arg}");
            }
        }

        profilePath ??= Path.Combine(gtsPath, "profiles", "Gate to Sovngarde Anniversary Edition Upgrade");
        var outputPath = output.EndsWith(".sqlite", StringComparison.OrdinalIgnoreCase)
            ? output
            : Path.Combine(output, "item-recipes.sqlite");
        return new Options(Path.GetFullPath(gtsPath), Path.GetFullPath(profilePath), Path.GetFullPath(outputPath), contains, maxSeconds);
    }

    private static void PrintHelpAndExit()
    {
        Console.WriteLine("Usage: GtsItemRecipeExporter [--gts-path PATH] [--profile PATH] [--out PATH] [--contains TEXT] [--max-seconds N]");
        Environment.Exit(0);
    }
}

internal sealed record StageResult(ModKey[] LoadOrder);
internal sealed record Manifest(DateTimeOffset GeneratedAt, string GtsPath, string ProfilePath, string StagedDataPath, int ActivePluginCount, int RecipeCount, string Source, double StageSeconds, double EnvironmentSeconds, double ExportSeconds, double TotalSeconds);
internal sealed record RecipeRow(string RecipeFormId, string? RecipeEditorId, string SourcePlugin, string CreatedFormId, string? CreatedEditorId, string? CreatedName, string? CreatedType, double? CreatedValue, double? CreatedWeight, int CreatedCount, string? WorkbenchFormId, string? WorkbenchEditorId, int ConditionCount, List<IngredientRow> Ingredients);
internal sealed record IngredientRow(string FormId, string? EditorId, string? Name, string? Type, double? Value, double? Weight, int Count);
