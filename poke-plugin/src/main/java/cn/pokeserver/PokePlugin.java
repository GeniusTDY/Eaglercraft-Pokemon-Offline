package cn.pokeserver;

import org.bukkit.plugin.java.JavaPlugin;

import java.util.logging.Level;




public class PokePlugin extends JavaPlugin {

    private PokeManager manager;
    private BattleManager battleManager;

    @Override
    public void onEnable() {
        saveDefaultConfig();

        manager = new PokeManager(this);
        manager.onEnable();

        battleManager = new BattleManager(this);

        getServer().getPluginManager().registerEvents(new PokeListener(this), this);

        PokeCommands cmds = new PokeCommands(this);
        String[] names = {"poke", "pokespawn", "pokeball", "party", "box", "deposit", "withdraw",
                "summon", "dismiss", "pokeinfo", "release", "battle", "attack", "heal"};
        for (String n : names) {
            getCommand(n).setExecutor(cmds);
            getCommand(n).setTabCompleter(cmds);
        }

        getLogger().log(Level.INFO, "宝可梦插件已启用 (PokeServer v1.0.0)");
    }

    @Override
    public void onDisable() {
        if (manager != null) manager.onDisable();
        getLogger().log(Level.INFO, "宝可梦插件已禁用");
    }

    public PokeManager getManager() { return manager; }
    public BattleManager getBattleManager() { return battleManager; }
}
