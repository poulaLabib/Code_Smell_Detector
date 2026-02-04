package commons.col.v2;

// [SMELL:DeadCode]
public class OrchestratorCommonscol9 {

    public void liveMethod() {
        System.out.println("alive");
    }

    // DEAD: never called
    private void unusedHelper0(int x) {
        int y = x * 5;
        System.out.println("dead " + y);
    }

    // DEAD: never called
    private void unusedHelper1(int x) {
        int y = x * 5;
        System.out.println("dead " + y);
    }

    // DEAD: never called
    private void unusedHelper2(int x) {
        int y = x * 6;
        System.out.println("dead " + y);
    }

    // DEAD: never called
    private void unusedHelper3(int x) {
        int y = x * 5;
        System.out.println("dead " + y);
    }

}