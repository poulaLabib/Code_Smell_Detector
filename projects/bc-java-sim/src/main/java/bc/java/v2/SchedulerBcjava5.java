package bc.java.v2;

import java.util.*;

// [SMELL:Clean]
public class SchedulerBcjava5 {

    private final List<String> items;

    public SchedulerBcjava5() { this.items = new ArrayList<>(); }

    public void add(String item) {
        if (item != null && !item.isEmpty()) items.add(item);
    }

    public List<String> getItems() { return Collections.unmodifiableList(items); }
    public int size() { return items.size(); }
    public boolean contains(String item) { return items.contains(item); }
}