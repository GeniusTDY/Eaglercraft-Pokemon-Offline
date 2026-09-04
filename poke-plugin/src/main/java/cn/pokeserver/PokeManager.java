package cn.pokeserver;

import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.entity.Entity;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.entity.Wolf;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.ShapelessRecipe;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.scheduler.BukkitRunnable;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.UUID;




public class PokeManager {

    private final PokePlugin plugin;
    private final Map<UUID, PlayerData> data = new HashMap<>();
    private final Map<UUID, Pokemon> wildPokemon = new HashMap<>();   
    private final Map<UUID, UUID> summoned = new HashMap<>();          
    private final Random random = new Random();

    
    private int wildSpawnInterval = 60;   
    private int wildSpawnRadius = 24;     
    private int maxWildLevel = 30;
    private int starterAmount = 5;

    private File dataDir;

    public PokeManager(PokePlugin plugin) {
        this.plugin = plugin;
    }

    public void onEnable() {
        FileConfiguration cfg = plugin.getConfig();
        cfg.options().copyDefaults(true);
        wildSpawnInterval = cfg.getInt("wildSpawnInterval", 60);
        wildSpawnRadius = cfg.getInt("wildSpawnRadius", 24);
        maxWildLevel = cfg.getInt("maxWildLevel", 30);
        starterAmount = cfg.getInt("starterAmount", 5);
        plugin.saveConfig();

        dataDir = new File(plugin.getDataFolder(), "players");
        if (!dataDir.exists()) dataDir.mkdirs();

        registerRecipe();

        
        new BukkitRunnable() {
            @Override
            public void run() {
                int removed = 0;
                for (World w : plugin.getServer().getWorlds()) {
                    for (Entity e : w.getEntities()) {
                        if (e instanceof LivingEntity
                                && e.getCustomName() != null
                                && e.getCustomName().contains("野生的")) {
                            e.remove();
                            removed++;
                        }
                    }
                }
                if (removed > 0) {
                    plugin.getLogger().info("已清理遗留的野生宝可梦实体 x" + removed);
                }
            }
        }.runTaskLater(plugin, 20L);

        
        new BukkitRunnable() {
            @Override
            public void run() {
                if (plugin.getServer().getOnlinePlayers().size() > 0) {
                    spawnWildPokemon();
                }
            }
        }.runTaskTimer(plugin, wildSpawnInterval * 20L, wildSpawnInterval * 20L);
    }

    public void onDisable() {
        
        for (PlayerData pd : data.values()) pd.save(dataDir);
        data.clear();
    }

    public PlayerData getData(Player p) {
        return data.computeIfAbsent(p.getUniqueId(), id -> PlayerData.load(dataDir, id));
    }

    
    public void giveStarter(Player p) {
        PlayerData pd = getData(p);
        if (pd.getTeam().isEmpty()) {
            pd.getTeam().add(new Pokemon(EntityType.CHICKEN, 1));
            p.sendMessage(ChatColor.GOLD + "════ 欢迎来到宝可梦世界 ════");
            p.sendMessage(ChatColor.GREEN + "你获得了新手宝可梦【咯咯鸡】Lv.1！");
            p.sendMessage(ChatColor.GREEN + "你获得了 5 个精灵球！");
            p.sendMessage(ChatColor.YELLOW + "输入 /poke 查看帮助，快出发去捕捉野生宝可梦吧！");
            givePokeball(p, starterAmount);
            pd.save(dataDir);
        }
    }

    

    public ItemStack createPokeball(int amount) {
        ItemStack item = new ItemStack(Material.SLIME_BALL, amount);
        ItemMeta meta = item.getItemMeta();
        meta.setDisplayName(ChatColor.RED + "⚫ 精灵球");
        List<String> lore = new ArrayList<>();
        lore.add(ChatColor.GRAY + "手持精灵球，右键点击野生的宝可梦进行捕捉");
        lore.add(ChatColor.GRAY + "捕捉成功率与宝可梦等级、种族有关");
        meta.setLore(lore);
        item.setItemMeta(meta);
        return item;
    }

    public boolean isPokeball(ItemStack item) {
        if (item == null || item.getType() != Material.SLIME_BALL) return false;
        if (!item.hasItemMeta() || !item.getItemMeta().hasDisplayName()) return false;
        return item.getItemMeta().getDisplayName().contains("精灵球");
    }

    public void givePokeball(Player p, int amount) {
        p.getInventory().addItem(createPokeball(amount));
    }

    private void registerRecipe() {
        ShapelessRecipe recipe = new ShapelessRecipe(createPokeball(1));
        recipe.addIngredient(Material.EGG);
        recipe.addIngredient(Material.IRON_INGOT);
        plugin.getServer().addRecipe(recipe);
    }

    

    public void spawnWildPokemon() {
        List<Player> online = new ArrayList<>(plugin.getServer().getOnlinePlayers());
        Player target = online.get(random.nextInt(online.size()));
        Location base = target.getLocation();

        List<EntityType> pool = new ArrayList<>(PokeSpecies.wildPool());
        EntityType type = pool.get(random.nextInt(pool.size()));
        int level = 1 + random.nextInt(maxWildLevel);

        World world = base.getWorld();
        int x = base.getBlockX() + (random.nextInt(wildSpawnRadius * 2) - wildSpawnRadius);
        int z = base.getBlockZ() + (random.nextInt(wildSpawnRadius * 2) - wildSpawnRadius);
        int y = findSurfaceY(world, x, z);
        Location loc = new Location(world, x + 0.5, y, z + 0.5);

        Entity e = world.spawnEntity(loc, type);
        if (e instanceof LivingEntity) {
            LivingEntity le = (LivingEntity) e;
            PokeSpecies.Species sp = PokeSpecies.get(type);
            le.setCustomName(ChatColor.GOLD + "野生的 " + ChatColor.AQUA + sp.name
                    + ChatColor.WHITE + " Lv." + level);
            le.setCustomNameVisible(true);
            le.setRemoveWhenFarAway(false);
        }
        wildPokemon.put(e.getUniqueId(), new Pokemon(type, level));

        
        PokeSpecies.Species sp = PokeSpecies.get(type);
        target.sendTitle(ChatColor.GOLD + "野生的 " + ChatColor.AQUA + sp.name + ChatColor.GOLD + " 出现了！",
                ChatColor.WHITE + "手持精灵球右键它进行捕捉", 10, 60, 20);
        target.sendActionBar(ChatColor.AQUA + sp.name + ChatColor.WHITE + " Lv." + level);

        plugin.getLogger().info("野生宝可梦刷新: " + sp.name
                + " Lv." + level + " @ " + x + "," + y + "," + z + " (附近玩家 " + target.getName() + ")");
    }

    
    public void spawnWildPokemonNear(Player p) {
        Location eye = p.getEyeLocation();
        org.bukkit.util.Vector dir = eye.getDirection();
        Location loc = eye.clone().add(dir.multiply(3));
        loc.setY(loc.getY() - 1);
        loc = loc.getWorld().getHighestBlockAt(loc).getLocation().add(0.5, 1, 0.5);

        List<EntityType> pool = new ArrayList<>(PokeSpecies.wildPool());
        EntityType type = pool.get(random.nextInt(pool.size()));
        int level = 1 + random.nextInt(maxWildLevel);

        Entity e = loc.getWorld().spawnEntity(loc, type);
        if (e instanceof LivingEntity) {
            LivingEntity le = (LivingEntity) e;
            PokeSpecies.Species sp = PokeSpecies.get(type);
            le.setCustomName(ChatColor.GOLD + "野生的 " + ChatColor.AQUA + sp.name
                    + ChatColor.WHITE + " Lv." + level);
            le.setCustomNameVisible(true);
            le.setRemoveWhenFarAway(false);
        }
        wildPokemon.put(e.getUniqueId(), new Pokemon(type, level));

        
        PokeSpecies.Species sp = PokeSpecies.get(type);
        p.sendTitle(ChatColor.GOLD + "野生的 " + ChatColor.AQUA + sp.name + ChatColor.GOLD + " 出现了！",
                ChatColor.WHITE + "手持精灵球右键它进行捕捉", 10, 60, 20);
        p.sendActionBar(ChatColor.AQUA + sp.name + ChatColor.WHITE + " Lv." + level);

        plugin.getLogger().info("调试刷新野生宝可梦: " + sp.name
                + " Lv." + level + " @ " + loc.getBlockX() + "," + loc.getBlockY() + "," + loc.getBlockZ());
    }

    
    private int findSurfaceY(World world, int x, int z) {
        int y = world.getHighestBlockYAt(x, z);
        for (; y > 1; y--) {
            Material m = world.getBlockAt(x, y, z).getType();
            if (m == Material.AIR || m == Material.LEAVES || m == Material.LEAVES_2
                    || m == Material.LOG || m == Material.LOG_2
                    || m == Material.SNOW || m == Material.LONG_GRASS
                    || m == Material.DOUBLE_PLANT || m == Material.RED_ROSE
                    || m == Material.YELLOW_FLOWER || m == Material.VINE
                    || m == Material.WATER_LILY) {
                continue; 
            }
            return y + 1;
        }
        return world.getHighestBlockYAt(x, z) + 1;
    }

    public boolean isWildPokemon(Entity e) {
        return wildPokemon.containsKey(e.getUniqueId());
    }

    public Pokemon getWildPokemon(Entity e) {
        return wildPokemon.get(e.getUniqueId());
    }

    public void removeWild(Entity e) {
        wildPokemon.remove(e.getUniqueId());
    }

    

    
    public boolean catchAttempt(Player player, Entity entity) {
        Pokemon wild = wildPokemon.get(entity.getUniqueId());
        if (wild == null) return false;

        PokeSpecies.Species sp = PokeSpecies.get(wild.getSpecies());
        if (sp == null) return false;

        
        double levelFactor = Math.max(0.05, 1.0 - (wild.getLevel() - 1) * 0.025);
        double chance = sp.catchRate * levelFactor;
        boolean success = random.nextDouble() < chance;

        
        consumePokeball(player);

        wildPokemon.remove(entity.getUniqueId());
        entity.remove();

        if (success) {
            addToPlayer(player, wild);
            player.playSound(player.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 1f, 1.5f);
            player.sendMessage(ChatColor.GREEN + "捕捉成功！你获得了 "
                    + ChatColor.AQUA + sp.name + ChatColor.GREEN + " Lv." + wild.getLevel() + "！");
            player.sendActionBar(ChatColor.GREEN + "捕捉成功！获得 "
                    + ChatColor.AQUA + sp.name + ChatColor.WHITE + " Lv." + wild.getLevel());
        } else {
            player.playSound(player.getLocation(), Sound.ENTITY_ITEM_BREAK, 1f, 0.8f);
            player.sendMessage(ChatColor.RED + "哎呀！" + ChatColor.AQUA + sp.name
                    + ChatColor.RED + " 挣脱了精灵球逃走了...");
            player.sendActionBar(ChatColor.RED + "哎呀！" + ChatColor.AQUA + sp.name
                    + ChatColor.RED + " 挣脱了精灵球逃走了...");
        }
        return success;
    }

    private void consumePokeball(Player player) {
        ItemStack hand = player.getInventory().getItemInMainHand();
        if (isPokeball(hand)) {
            int n = hand.getAmount() - 1;
            if (n <= 0) player.getInventory().setItemInMainHand(null);
            else hand.setAmount(n);
        }
    }

    
    public void addToPlayer(Player player, Pokemon p) {
        PlayerData pd = getData(player);
        if (pd.getTeam().size() < PlayerData.MAX_TEAM) {
            pd.getTeam().add(p);
            player.sendMessage(ChatColor.YELLOW + "（已加入队伍，当前 " + pd.getTeam().size() + "/" + PlayerData.MAX_TEAM + "）");
        } else {
            if (pd.getBox().size() < PlayerData.MAX_BOX) {
                pd.getBox().add(p);
                player.sendMessage(ChatColor.YELLOW + "（队伍已满，已存入箱子）");
            } else {
                player.sendMessage(ChatColor.RED + "队伍和箱子都已满！宝可梦放生了...");
            }
        }
        pd.save(dataDir);
    }

    

    public void summon(Player player, Pokemon p) {
        dismiss(player);
        Location loc = player.getLocation();
        Entity e = player.getWorld().spawnEntity(loc, p.getSpecies());
        if (e instanceof LivingEntity) {
            LivingEntity le = (LivingEntity) e;
            if (le instanceof Wolf) {
                Wolf w = (Wolf) le;
                w.setTamed(true);
                w.setOwner(player);
            }
            le.setCustomName(ChatColor.YELLOW + p.getNickname()
                    + ChatColor.WHITE + " Lv." + p.getLevel());
            le.setCustomNameVisible(true);
            le.setCanPickupItems(false);
            le.setRemoveWhenFarAway(false);
        }
        summoned.put(player.getUniqueId(), e.getUniqueId());
        player.playSound(loc, Sound.ENTITY_PLAYER_LEVELUP, 1f, 1.2f);
        player.sendMessage(ChatColor.GREEN + "你召唤了 " + ChatColor.AQUA + p.getNickname()
                + ChatColor.GREEN + " Lv." + p.getLevel() + "！");
        player.sendActionBar(ChatColor.GREEN + "你召唤了 "
                + ChatColor.AQUA + p.getNickname() + ChatColor.WHITE + " Lv." + p.getLevel());
    }

    public void dismiss(Player player) {
        UUID id = summoned.remove(player.getUniqueId());
        if (id != null) {
            for (World w : plugin.getServer().getWorlds()) {
                Entity e = w.getEntity(id);
                if (e != null) { e.remove(); break; }
            }
        }
    }

    public Entity getSummonedEntity(Player player) {
        UUID id = summoned.get(player.getUniqueId());
        if (id == null) return null;
        for (World w : plugin.getServer().getWorlds()) {
            Entity e = w.getEntity(id);
            if (e != null) return e;
        }
        summoned.remove(player.getUniqueId());
        return null;
    }

    public boolean hasSummoned(Player player) {
        return getSummonedEntity(player) != null;
    }

    
    public Player getSummonedOwner(Entity entity) {
        for (Map.Entry<UUID, UUID> en : summoned.entrySet()) {
            if (en.getValue().equals(entity.getUniqueId())) {
                return plugin.getServer().getPlayer(en.getKey());
            }
        }
        return null;
    }

    

    public void grantExp(Player player, int amount) {
        Entity e = getSummonedEntity(player);
        if (e == null) return;
        PlayerData pd = getData(player);
        Pokemon p = null;
        for (Pokemon x : pd.getTeam()) {
            if (x.getSpecies() == e.getType()) { p = x; break; }
        }
        if (p == null) return;

        p.addExp(amount);
        if (p.checkLevelUp()) {
            player.sendMessage(ChatColor.AQUA + p.getNickname() + ChatColor.GREEN
                    + " 升级到了 Lv." + p.getLevel() + "！");
            player.playSound(player.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 1f, 1.5f);
            player.sendActionBar(ChatColor.AQUA + p.getNickname() + ChatColor.GREEN
                    + " 升级到了 Lv." + p.getLevel() + "！");
            e.setCustomName(ChatColor.YELLOW + p.getNickname() + ChatColor.WHITE + " Lv." + p.getLevel());
            
            PokeSpecies.Species sp = PokeSpecies.get(p.getSpecies());
            if (sp != null && sp.evolveTo != null && p.getLevel() >= sp.evolveLevel) {
                evolve(player, p, e, sp.evolveTo);
            }
        }
        pd.save(dataDir);
    }

    private void evolve(Player player, Pokemon p, Entity e, EntityType to) {
        String old = p.getNickname();
        p.setSpecies(to);
        p.setHp(p.maxHp());
        if (e != null && e.isValid()) {
            Location loc = e.getLocation();
            e.remove();
            Entity ne = player.getWorld().spawnEntity(loc, to);
            if (ne instanceof LivingEntity) {
                LivingEntity le = (LivingEntity) ne;
                if (le instanceof Wolf) {
                    Wolf w = (Wolf) le;
                    w.setTamed(true);
                    w.setOwner(player);
                }
                le.setCustomName(ChatColor.YELLOW + p.getNickname() + ChatColor.WHITE + " Lv." + p.getLevel());
                le.setCustomNameVisible(true);
                le.setCanPickupItems(false);
                le.setRemoveWhenFarAway(false);
            }
            summoned.put(player.getUniqueId(), ne.getUniqueId());
        }
        player.playSound(player.getLocation(), Sound.ENTITY_WITHER_SPAWN, 1f, 0.5f);
        player.sendMessage(ChatColor.GOLD + "★ 进化！" + ChatColor.AQUA + old
                + ChatColor.GOLD + " 进化成了 " + ChatColor.AQUA + p.getNickname() + ChatColor.GOLD + "！");
        player.sendTitle(ChatColor.GOLD + "★ 进化！",
                ChatColor.AQUA + old + ChatColor.GOLD + " → " + ChatColor.AQUA + p.getNickname(), 10, 60, 20);
    }

    public Random getRandom() { return random; }
}
