package cn.pokeserver;

import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;




public class PlayerData {
    public static final int MAX_TEAM = 6;
    public static final int MAX_BOX = 30;

    private final UUID uuid;
    private final List<Pokemon> team = new ArrayList<>();
    private final List<Pokemon> box = new ArrayList<>();

    public PlayerData(UUID uuid) {
        this.uuid = uuid;
    }

    public UUID getUuid() { return uuid; }
    public List<Pokemon> getTeam() { return team; }
    public List<Pokemon> getBox() { return box; }

    
    public void save(File dir) {
        File f = new File(dir, uuid.toString() + ".yml");
        YamlConfiguration c = new YamlConfiguration();
        int i = 0;
        for (Pokemon p : team) p.toSection(c.createSection("team." + (i++)));
        i = 0;
        for (Pokemon p : box) p.toSection(c.createSection("box." + (i++)));
        try {
            c.save(f);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    
    public static PlayerData load(File dir, UUID uuid) {
        PlayerData pd = new PlayerData(uuid);
        File f = new File(dir, uuid.toString() + ".yml");
        if (f.exists()) {
            YamlConfiguration c = YamlConfiguration.loadConfiguration(f);
            ConfigurationSection team = c.getConfigurationSection("team");
            if (team != null) {
                for (String k : team.getKeys(false)) {
                    pd.team.add(Pokemon.fromSection(team.getConfigurationSection(k)));
                }
            }
            ConfigurationSection box = c.getConfigurationSection("box");
            if (box != null) {
                for (String k : box.getKeys(false)) {
                    pd.box.add(Pokemon.fromSection(box.getConfigurationSection(k)));
                }
            }
        }
        return pd;
    }
}
