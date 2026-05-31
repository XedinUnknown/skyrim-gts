unit ExportItemRecipeIndex;

// xEdit script template for exporting a searchable item and COBJ recipe index.
// Run from xEdit/SSEEdit with the active load order loaded. This is intended as
// the authoritative route because xEdit resolves overrides, links, localized
// names, and conditions using its decoded record definitions.

interface
implementation

uses xEditAPI, Classes, SysUtils, StrUtils;

var
  OutLines: TStringList;

function JsonEscape(s: string): string;
begin
  Result := StringReplace(s, '\', '\\', [rfReplaceAll]);
  Result := StringReplace(Result, '"', '\"', [rfReplaceAll]);
  Result := StringReplace(Result, #13#10, '\n', [rfReplaceAll]);
  Result := StringReplace(Result, #10, '\n', [rfReplaceAll]);
  Result := StringReplace(Result, #13, '\n', [rfReplaceAll]);
end;

function Q(s: string): string;
begin
  Result := '"' + JsonEscape(s) + '"';
end;

function SafeEditValue(e: IInterface; path: string): string;
begin
  Result := '';
  if Assigned(e) then
    try
      Result := GetElementEditValues(e, path);
    except
      Result := '';
    end;
end;

function LinkedName(e: IInterface; path: string): string;
var
  linkElem, linked: IInterface;
begin
  Result := '';
  linkElem := ElementByPath(e, path);
  if Assigned(linkElem) then begin
    linked := LinksTo(linkElem);
    if Assigned(linked) then
      Result := DisplayName(linked);
  end;
end;

procedure AddJsonLine(line: string);
begin
  if OutLines.Count > 1 then
    OutLines[OutLines.Count - 1] := OutLines[OutLines.Count - 1] + ',';
  OutLines.Add(line);
end;

procedure ExportItem(rec: IInterface);
var
  w: IInterface;
  sig, line: string;
begin
  w := WinningOverride(rec);
  if not Assigned(w) then
    w := rec;

  sig := Signature(w);
  if not ((sig = 'ARMO') or (sig = 'WEAP') or (sig = 'ALCH') or (sig = 'INGR') or
          (sig = 'MISC') or (sig = 'BOOK') or (sig = 'AMMO') or (sig = 'SCRL')) then
    Exit;

  line := '  {"kind":"item"' +
    ',"signature":' + Q(sig) +
    ',"plugin":' + Q(GetFileName(GetFile(w))) +
    ',"formid":' + Q(IntToHex(GetLoadOrderFormID(w), 8)) +
    ',"editor_id":' + Q(EditorID(w)) +
    ',"name":' + Q(SafeEditValue(w, 'FULL')) +
    ',"display":' + Q(DisplayName(w)) +
    '}';
  AddJsonLine(line);
end;

procedure ExportRecipe(rec: IInterface);
var
  w, items, item: IInterface;
  i: integer;
  ingredients, ingredientName, ingredientCount, line: string;
begin
  w := WinningOverride(rec);
  if not Assigned(w) then
    w := rec;
  if Signature(w) <> 'COBJ' then
    Exit;

  ingredients := '[';
  items := ElementByPath(w, 'Items');
  if Assigned(items) then begin
    for i := 0 to ElementCount(items) - 1 do begin
      item := ElementByIndex(items, i);
      ingredientName := LinkedName(item, 'CNTO\Item');
      ingredientCount := SafeEditValue(item, 'CNTO\Count');
      if i > 0 then
        ingredients := ingredients + ',';
      ingredients := ingredients + '{"item":' + Q(ingredientName) + ',"count":' + Q(ingredientCount) + '}';
    end;
  end;
  ingredients := ingredients + ']';

  line := '  {"kind":"recipe"' +
    ',"signature":"COBJ"' +
    ',"plugin":' + Q(GetFileName(GetFile(w))) +
    ',"formid":' + Q(IntToHex(GetLoadOrderFormID(w), 8)) +
    ',"editor_id":' + Q(EditorID(w)) +
    ',"created":' + Q(LinkedName(w, 'CNAM')) +
    ',"workbench":' + Q(LinkedName(w, 'BNAM')) +
    ',"output_count":' + Q(SafeEditValue(w, 'NAM1')) +
    ',"ingredients":' + ingredients +
    ',"conditions":' + Q(SafeEditValue(w, 'Conditions')) +
    '}';
  AddJsonLine(line);
end;

procedure WalkGroup(group: IInterface);
var
  i: integer;
  child: IInterface;
begin
  if not Assigned(group) then
    Exit;
  for i := 0 to ElementCount(group) - 1 do begin
    child := ElementByIndex(group, i);
    if ElementType(child) = etMainRecord then begin
      ExportItem(child);
      ExportRecipe(child);
    end else begin
      WalkGroup(child);
    end;
  end;
end;

function Initialize: integer;
var
  i: integer;
  f: IInterface;
begin
  OutLines := TStringList.Create;
  OutLines.Add('[');

  for i := 0 to FileCount - 1 do begin
    f := FileByIndex(i);
    WalkGroup(GroupBySignature(f, 'ARMO'));
    WalkGroup(GroupBySignature(f, 'WEAP'));
    WalkGroup(GroupBySignature(f, 'ALCH'));
    WalkGroup(GroupBySignature(f, 'INGR'));
    WalkGroup(GroupBySignature(f, 'MISC'));
    WalkGroup(GroupBySignature(f, 'BOOK'));
    WalkGroup(GroupBySignature(f, 'AMMO'));
    WalkGroup(GroupBySignature(f, 'SCRL'));
    WalkGroup(GroupBySignature(f, 'COBJ'));
  end;

  OutLines.Add(']');
  Result := 0;
end;

function Finalize: integer;
var
  outPath: string;
begin
  outPath := ProgramPath + 'item-recipe-index.json';
  OutLines.SaveToFile(outPath);
  AddMessage('Exported item and recipe index to ' + outPath);
  OutLines.Free;
  Result := 0;
end;

end.
