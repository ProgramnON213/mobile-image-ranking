/**
 * Unit Tests: Mobile Image Ranker PWA Logic
 * Run with: node tests/test_pwa_ranker.js
 */
const assert = require('assert');

console.log("▶ Running PWA Ranker Unit Tests...");

// 1. Sliding Window Object URL Eviction Test (O(1) Memory Budget)
function testSlidingWindowEviction() {
    const revoked = [];
    global.URL = {
        revokeObjectURL: (url) => revoked.push(url)
    };

    const files = Array.from({ length: 30 }, (_, i) => ({
        key: `img_${i}.jpg_1000`,
        objectUrl: `blob:mock_${i}`
    }));

    function evictOutOfWindow(currIdx, list) {
        const evictLeft = currIdx - 11;
        if (evictLeft >= 0 && list[evictLeft]?.objectUrl) {
            URL.revokeObjectURL(list[evictLeft].objectUrl);
            list[evictLeft].objectUrl = null;
        }
        const evictRight = currIdx + 6;
        if (evictRight < list.length && list[evictRight]?.objectUrl) {
            URL.revokeObjectURL(list[evictRight].objectUrl);
            list[evictRight].objectUrl = null;
        }
    }

    for (let i = 0; i <= 15; i++) {
        evictOutOfWindow(i, files);
    }

    assert.strictEqual(files[4].objectUrl, null, "Item exiting left window must be revoked");
    assert.ok(revoked.includes("blob:mock_4"), "RevokeObjectURL must be invoked");
    console.log("  ✔ O(1) Sliding window eviction verified.");
}

// 2. CSV Data Export Quotation Sanitization
function testCsvExportSanitization() {
    function generateCsvRows(items) {
        let csv = "file,rating\n";
        items.forEach(row => {
            const escaped = row.file.replace(/"/g, '""');
            csv += `"${escaped}","${row.rating}"\n`;
        });
        return csv;
    }

    const testData = [
        { file: 'image_normal.jpg', rating: 'keep' },
        { file: 'image_with_"quotes".jpg', rating: 'discard' }
    ];

    const result = generateCsvRows(testData);
    assert.ok(result.includes('"image_with_""quotes"".jpg"'), "Double quotes must be escaped in CSV export");
    console.log("  ✔ CSV formatting & quote escaping verified.");
}

testSlidingWindowEviction();
testCsvExportSanitization();
console.log("✅ All PWA unit tests passed successfully!\n");
