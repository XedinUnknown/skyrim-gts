# Gameplay Systems

Use this when explaining GTS mechanics. Do not assume vanilla behavior when GTS changes it.

## Starting A New Game

- Alternate Perspective replaces the vanilla intro.
- The starting room contains useful gear, potions, food, gold, jewelry, and the Big Book of Traits.
- The player may choose up to three traits before leaving the starting room. Traits are intended to stick for the playthrough.
- The Gear of Balance switches between the default GTS experience and Story Mode. It can also be found behind Helgen Inn later.
- Story Mode is separate from game difficulty and Survival Mode.
- Story Mode immediately enables compass, sneak eye, and map marker; makes high-damage combat easier; increases starting carry weight; reduces stress gain; prevents follower death/injury; makes sneaking not consume stamina; gives more empty potion bottles; and changes vampire sun/stage-4 hostility behavior.
- All questlines are available regardless of alternate start. Selecting Dragonborn is not required.

## Interface And World Rules

- Compass, sneak eye, and player map marker are disabled by default and unlocked through Campfire Skills of the Wild Wayfarer perks: `Spatial Awareness` for compass/map marker and `Sixth Sense` for sneak eye. Story Mode bypasses this.
- Menus do not pause by default because of Skyrim Souls. Quick menu and hotkeys are important.
- Default potion hotkeys from the wiki: `V`, `B`, and `N` for health, stamina, and magicka potions.
- Containers have weight limits. This is intended and can be adjusted through collection tweaks.
- Tempered gear degrades from combat by reducing temper level; items do not fully break. Whetstones and blacksmith hammers can restore temper in the field at lower effectiveness.
- Couriers may store pending letters in Whiterun Customs Hall if delivery seems broken.

## Combat

- GTS combat is more lethal than vanilla but remains recognizably Skyrim.
- Locations use a hybrid of leveled and unleveled enemies. Early Bleak Falls Barrow is not recommended.
- Magic resistance matters much more than in vanilla.
- Resource management for health, stamina, and magicka is central.
- Blocking and bashing are important, especially against groups.
- Retreat is a valid answer when an area is too strong.
- Base regeneration observed on wiki: health 1%, magicka 3%, stamina 5%; in combat health 0.5%, magicka 1.5%, stamina 2.5%. Survival Mode changes these.
- Difficulty multipliers observed on wiki: Novice 1.25x dealt / 0.75x received; Apprentice 1.00/1.00; Adept 1.00/1.50; Expert 0.80/2.00; Master 0.60/3.00; Legendary 0.40/4.00.

## Survival And Travel

- Survival Mode is enabled by default and changes hunger, exhaustion, warmth, fast travel, health regeneration, and leveling.
- Hunger reduces maximum stamina and melee damage at worse stages. Vampires hunger for blood instead; liches do not hunger.
- Exhaustion reduces maximum magicka and experience gained. Liches do not get exhausted; vampires/lycanthropes cannot get rested bonuses.
- Cold reduces maximum health and movement speed. Warmth effectiveness is capped; Nords and Khajiit have extra cold resistance; liches are immune; vampires are much slower to get cold.
- Survival Mode disables base health regeneration; health regen requires items or effects.
- Leveling requires sleeping. The wait key can be used while in bed. Shift+E sleeping on chairs is possible for short sleeps but gives a stamina debuff.
- Fast travel is restricted by Journeyman and usually requires a Travel Pack. Travel Packs are craftable from leather, leather strips, firewood, and a torch.
- Fast traveling on horseback can reduce survival drain and allow over-encumbered travel.
- Inns outside major holds can call carriage drivers with broader destinations.
- Horses can be called with `H`; Shift+H near the horse opens inventory.
- Teleportation spells such as Mark/Recall and temple Intervention spells provide magic travel alternatives.
- Bend Will dragon flight can still provide vanilla-style fast travel.

## Stress, Fear, Injuries

- Stress is gained mainly from being hit in combat and reduces maximum magicka and stamina by severity.
- Stress can also increase from follower death, bad music, or a bad skooma trip.
- Stress can be reduced by petting animals, alcohol, comfort/warm food, bathing, fishing, reading, praying, meditating, playing instruments, sleeping in an inn/house, and conquering fears.
- Fear can develop after surviving at very low health against an enemy type. It blurs vision, reduces damage against that enemy type, and increases stress gain.
- Killing feared enemies after being hit can overcome the fear, remove stress, and grant permanent damage against that enemy type.
- Injuries are added by Wounds. They affect head, torso, arms, and legs with location-specific penalties.
- The first injury triggers a courier note directing the player to temple books that grant the Treat Wounds power.
- Supplies worth carrying include medicinal alcohol, bandages, needle/thread, firewood for splints, hanging moss, blue mountain flower, torches/fire spells, and tundra cotton.

## Character, Traits, Races, Stones

- Character creation uses RaceMenu and expanded visual options.
- Races use Aetherius-style changes and matter more than vanilla.
- GTS caps individual magical resistances at 75%, including fire/frost/shock/poison/magic/absorption.
- Armor rating caps at 1000, for 90% physical resistance.
- Standing Stones are overhauled by Mundus. Do not use vanilla stone effects when advising builds.
- Traits are based on Biggie Traits with GTS changes. Most traits trade a strong benefit for a drawback and are best chosen for roleplay rather than min-maxing.
- Trait reselection is not intended, but the wiki documents `coc APStartCell` as a workaround. Warn not to leave through the alternate-start door mid-save; use `coc` to exit instead.

## Perks And Progression

- Default skill perks are overhauled by Adamant plus Hand to Hand and GTS-specific changes.
- Major global perk changes include increased critical damage, power attacks doubling critical damage, most perk effects stacking, armor rating reducible below 0, armor type determined by chest piece, bow/crossbow zoom available by default, armor slowing movement/increasing spell costs, stronger bound weapons, spell cost decreasing with skill level, longer buff spell durations, and legendary skills resetting to 75 rather than 15.
- Campfire Skills of the Wild adds five trees: Firecraft, Art of the Hunt, Culinary Arts, Beast Handling, and Wayfarer.
- Wayfarer unlocks compass, sneak eye, and player map marker.
- Thu'um perks come from Stormcrown with GTS edits. After Greybeard recognition, use the High Hrothgar Courtyard shrine behind the Whirlwind Sprint gate to meditate or trade 5 dragon souls for a perk point.
- Thu'um skill XP comes from dragons, souls, words of power, and shouting, preferably in combat. It contributes to character level. Perk points still come from normal level-up points unless trading souls.

## Food, Hunting, Camping

- Gourmet overhauls cooking. Food buffs can substantially affect regeneration and usually last 20 minutes, with ways to extend.
- Food types can separately boost health, stamina, and magicka regeneration.
- Water from waterskins slightly improves food bonuses.
- Alcohol and drugs have significant buffs/drawbacks and addiction risk.
- Hunting is expanded: pelts take time, carcasses can be carried with Shift+E, and city carcass sales may require permits or thane status.
- Campfire provides camping, tents, placeable furniture, and Skills of the Wild. Camping in cities is prohibited and can result in a fine if seen.

## Transformations

- Vampirism is significantly expanded. Sunlight damages vampires and suppresses regeneration. Stages affect strengths, weaknesses, powers, feeding, and hostility. Story Mode changes some vampire penalties.
- Vampire feeding options include nearly defeated enemies, unaware enemies, fallen enemies, and Potion of Blood.
- Werewolves can come from alternate start, Canis Hysteria, or the Companions. Companions lycanthropy is no longer mandatory if refused before the point of no return.
- Werewolves have Beast Senses, disease immunity, hunger mechanics, forced transformations, and can revert from beast form through Favorites.
- Werebears come from Tales of Skyrim - Berserkyr quests starting with Rudir at Four Shields Tavern in Dragon Bridge. They have automatic low-health combat transformations and are not easily regained after curing.
- Lichdom uses Undeath-related mods and has its own perk/support systems, but the wiki page may be sparse; verify current docs before detailed advice.
