document.addEventListener('DOMContentLoaded', () => {
    const totalInput = document.getElementById('total-amount');
    const bossInput = document.getElementById('boss-count');
    const subInput = document.getElementById('sub-count');
    const calcBtn = document.getElementById('calculate-btn');
    const resultContainer = document.getElementById('result-container');
    
    const resBoss = document.getElementById('res-boss');
    const resSub = document.getElementById('res-sub');
    const resRemainder = document.getElementById('res-remainder');

    calcBtn.addEventListener('click', () => {
        const total = parseInt(totalInput.value, 10) || 0;
        const bossCount = parseInt(bossInput.value, 10) || 0;
        const subCount = parseInt(subInput.value, 10) || 0;

        // 負の数に対するバリデーションを追加
        if (total < 0 || bossCount < 0 || subCount < 0) {
            alert('入力値にマイナスの値が含まれています。正しく入力してください。');
            return;
        }

        if (total === 0) {
            alert('総額を正しく入力してください。');
            return;
        }
        if (bossCount === 0 && subCount === 0) {
            alert('人数を入力してください。');
            return;
        }

        let bossPay = 0;
        let subPay = 0;

        if (subCount === 0) {
            // Only bosses
            const rawPay = total / bossCount;
            bossPay = Math.ceil(rawPay / 100) * 100;
        } else if (bossCount === 0) {
            // Only subs
            const rawPay = total / subCount;
            subPay = Math.ceil(rawPay / 100) * 100;
        } else {
            // Both boss and sub
            const rawSubPay = (total - (1000 * bossCount)) / (bossCount + subCount);
            const clampedSubPay = Math.max(0, rawSubPay);
            subPay = Math.ceil(clampedSubPay / 100) * 100;
            bossPay = subPay + 1000;
        }

        const totalCollected = (bossPay * bossCount) + (subPay * subCount);
        // 余り（積立金）は「集まった合計額」から「実際の総額」を引いて算出します
        const remainder = totalCollected - total;

        // Update DOM
        resBoss.textContent = bossPay.toLocaleString();
        resSub.textContent = subPay.toLocaleString();
        resRemainder.textContent = remainder.toLocaleString();

        // 0人のグループの行を非表示にする制御を追加
        const bossRow = document.getElementById('row-boss');
        const subRow = document.getElementById('row-sub');
        if (bossRow) bossRow.style.display = bossCount === 0 ? 'none' : 'flex';
        if (subRow) subRow.style.display = subCount === 0 ? 'none' : 'flex';

        resultContainer.style.display = 'block';
        
        // Scroll to results smoothly
        setTimeout(() => {
            resultContainer.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 10);
    });
});
