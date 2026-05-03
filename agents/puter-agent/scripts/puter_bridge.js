const { chromium } = require('playwright');

async function queryPuter(prompt, model = 'claude-3-5-sonnet') {
    const browser = await chromium.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
        // Load Puter's AI endpoint directly or via a wrapper
        // Puter requires a domain context to initialize puter.js correctly
        await page.goto('https://puter.com'); 
        
        // Inject Puter JS
        await page.addScriptTag({ url: 'https://js.puter.com/v2/' });

        // Execute the chat call
        const result = await page.evaluate(async ({p, m}) => {
            try {
                const response = await puter.ai.chat(p, { model: m });
                return typeof response === 'string' ? response : JSON.stringify(response);
            } catch (e) {
                return "ERROR: " + e.message;
            }
        }, {p: prompt, m: model});

        if (result.startsWith("ERROR:")) {
            throw new Error(result);
        }

        return result;
    } catch (error) {
        console.error("Puter Bridge Error:", error);
        throw error;
    } finally {
        await browser.close();
    }
}

if (require.main === module) {
    const prompt = process.argv[2] || "Hello Puter, are you working?";
    const model = process.argv[3] || "claude-3-5-sonnet";
    
    queryPuter(prompt, model)
        .then(res => {
            console.log("PUTER_RESPONSE: " + res);
            process.exit(0);
        })
        .catch(err => {
            console.error("FAILURE: " + err.message);
            process.exit(1);
        });
}

module.exports = { queryPuter };
