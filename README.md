Mount & Blade II: Bannerlord Coop (unofficial Pterodactyl egg)

This is unofficial. Don't bother the Coop mod devs or the game devs about it. If something breaks, message me on Discord or open an issue on GitHub. - I reccomend using an account without steam guard where possible, as otherwise you will need to provide your password each time the server restarts fpr steamcmd.

Found any issues? - Throw them on the repo's issues and I'll try get around to em: https://github.com/1294Angel/Unofficial-Bannerlord-Coop-Ptero-Egg

You need a steam account with Bannerlord owned and you must accept the Coop EULA yourself (Eula can be found in the mod files, start the server without accepting to see EULA in the files).

Requirements: 2 CPU cores (3 recommended), 8 GB RAM (more with many mods or players), 15 GB disk (more for mods, some are huge), and a Steam account that owns Bannerlord. 

The server uses one UDP port, aka, the allocation you give it. Give each server its own allocation.


SETUP FOR VANILLA

1. In the Panel go to Admin > Nests > Import Egg and import egg-bannerlord-coop.json.
2. Create a server from the egg.
3. Fill in Steam account and Steam password.
4. Leave Workshop mods empty.
5. Start the server. The first start downloads about 6 GB.
6. If Steam asks for a Steam Guard code, type it into the console.
7. The server stops after the download and tells you to accept the EULA. Open DedicatedServer/EULA.md in the Files tab and read it.
8. Set Accept Coop EULA to 1 and start the server again.
9. When the console prints SERVER UP, players can join.

SETUP FOR MODDING

1. Do all the steps in SETUP FOR VANILLA first, then stop the server.
2. On your PC open Steam, right click Bannerlord, Manage, Browse local files. Call that folder GAME.
3. On the server, in the Files tab, create the folder addons/client-view-dlls/ if it is not there.
4. Copy these six files from your PC into addons/client-view-dlls/ on the server. Do this again after each Bannerlord update.
   GAME/Modules/Native/bin/Win64_Shipping_Client/TaleWorlds.MountAndBlade.View.dll
   GAME/Modules/SandBox/bin/Win64_Shipping_Client/SandBox.View.dll
   GAME/Modules/SandBox/bin/Win64_Shipping_Client/SandBox.ViewModelCollection.dll
   GAME/bin/Win64_Shipping_Client/TaleWorlds.MountAndBlade.ViewModelCollection.dll
   GAME/bin/Win64_Shipping_Client/TaleWorlds.Core.ViewModelCollection.dll
   GAME/bin/Win64_Shipping_Client/TaleWorlds.CampaignSystem.ViewModelCollection.dll
5. Put the Workshop item IDs of your mods in Workshop mods, separated by commas. Order does not matter, the egg sorts the load order itself.
6. Start a campaign with the same mods on your PC and save it. The server cannot create a world for total conversions such as Empires of Europe, and this also works for other mods.
7. Upload the .sav file from Documents/Mount and Blade II Bannerlord/Game Saves/ on your PC to .wine/drive_c/users/container/Documents/Mount and Blade II Bannerlord/CoopData/DedicatedServer/Game Saves/ on the server. The .wine folder is hidden but shows in the Files tab.
8. Set World save name to the save's name without .sav.
9. If a mod is not on the Workshop, copy its folder from GAME/Modules/ModuleId to addons/local-mods/ModuleId on the server, so that SubModule.xml sits directly inside.
10. Start the server. The mods are downloaded and installed automatically.
11. Open modlist.txt in the Files tab. It lists every mod with its name and link. Players need the same mods, including any non-Workshop ones.
12. When the console prints SERVER UP, players can join.

Most mods work. Mods built for another game version, and mods whose animations, particles or sounds only exist in client files, do not.

TROUBLESHOOTING

Exits right after the download: the EULA is not accepted yet.
Steam asks for a code every start: use a dedicated account with Steam Guard by e-mail and type the code into the console.
Access Denied for one Workshop item: Steam refuses that item right now, often because it is being updated. Try again later.
Bad system call in the console: set Docker's seccomp-profile to unconfined in /etc/docker/daemon.json and restart Docker.
Exit code 82 with mods: a mod failed to load. Look for lines starting with loader: in logs/headless-diag.log and remove that mod.
Server hangs with no output and high CPU: a mod is showing a message box that cannot be answered. Check that mod's load-order requirements.