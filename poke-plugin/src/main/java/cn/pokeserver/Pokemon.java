package cn.pokeserver;

import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.EntityType;




public class Pokemon {
    private EntityType species;
    private String nickname;
    private int level;
    private int exp;
    private int hp; 

    public Pokemon(EntityType species, int level) {
        this.species = species;
        this.level = level;
        this.exp = 0;
        this.nickname = PokeSpecies.get(species) != null ? PokeSpecies.get(species).name : species.name();
        this.hp = maxHp();
    }

    
    public static Pokemon fromSection(ConfigurationSection s) {
        EntityType type;
        try {
            type = EntityType.valueOf(s.getString("species", "PIG"));
        } catch (Exception e) {
            type = EntityType.PIG;
        }
        Pokemon p = new Pokemon(type, s.getInt("level", 1));
        p.nickname = s.getString("nickname", p.nickname);
        p.exp = s.getInt("exp", 0);
        p.hp = s.getInt("hp", p.maxHp());
        return p;
    }

    
    public void toSection(ConfigurationSection s) {
        s.set("species", species.name());
        s.set("nickname", nickname);
        s.set("level", level);
        s.set("exp", exp);
        s.set("hp", hp);
    }

    public int maxHp() {
        return 20 + level * 2;
    }

    public EntityType getSpecies() { return species; }
    public void setSpecies(EntityType species) {
        this.species = species;
        PokeSpecies.Species sp = PokeSpecies.get(species);
        if (sp != null) this.nickname = sp.name;
    }
    public String getNickname() { return nickname; }
    public void setNickname(String nickname) { this.nickname = nickname; }
    public int getLevel() { return level; }
    public int getExp() { return exp; }
    public int getHp() { return hp; }
    public void setHp(int hp) { this.hp = hp; }

    
    public int expToNext() {
        return level * 20;
    }

    public void addExp(int amount) {
        exp += amount;
    }

    
    public boolean checkLevelUp() {
        boolean up = false;
        while (exp >= expToNext() && level < 100) {
            exp -= expToNext();
            level++;
            hp = maxHp();
            up = true;
        }
        return up;
    }
}
